import os
import re
import argparse
import scrapetube
import yt_dlp
import logging
import json
import subprocess
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

logging.basicConfig(level=logging.INFO)

def sanitize_filename(title):
    """
    Removes characters that are illegal in file names across different OS.
    """
    # Remove illegal characters
    sanitized = re.sub(r'[\\/*?:"<>|]', "", title)
    # Replace sequences of whitespace with a single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    # Trim leading/trailing whitespace
    return sanitized.strip()

def process_transcript_with_ai(raw_transcript_path, clean_transcript_path, video_title, video_url):
    """
    Processes a raw transcript file using gemini-cli to produce a clean version.
    """
    logging.info(f"  -> Processing with AI: {raw_transcript_path}")
    try:
        with open(raw_transcript_path, 'r', encoding='utf-8') as f:
            raw_transcript_data = f.read()

        # Construct a detailed prompt for the AI
        prompt = f"""
Please format the following raw YouTube transcript into a clean, readable, and well-structured markdown-compatible text. The context is a dharma talk from the Insight Meditation Center, related to Buddhism. The title of the talk is "{video_title}", with the url "{video_url}".

Your task is to transform the raw, fragmented transcript data into a polished, article-like format. Your output requirements:
-   **Include a disclaimer** The data should be prepended with a disclaimer like so: "This is an AI generated transcript of the video ["<video_title>"](<video_url>). It may contain inaccuracies."
-   **Simply output the article and nothing else** Do not use any tool to create a file. You are being called from a python script and your output is being saved directly to a markdown file, so do not include any other output other than the article.

Formatting requirements:
1.  **Combine Segments:** Merge the short text fragments into complete, grammatically correct sentences.
2.  **Punctuation & Capitalization:** Add appropriate punctuation (periods, commas, etc.) and correct capitalization.
3.  **Paragraphs:** Structure the text into logical paragraphs. A new paragraph should start when there is a clear shift in topic or a significant pause in the speech.
4.  **Readability:** Ensure the final text flows naturally and is easy to read. Remove conversational filler like 'uh' and 'um' unless they are essential for meaning.
5.  **No Timestamps:** Do not include any timestamps or metadata from the raw transcript in the final output.
6.  **Highlight likely transcribing errors** If a sentense is obviously wrong, likely due to a transcribing error (as lots of poly words / buddhism things are not common for transcribing), marking as [?], [word], or other appropriate markings.
7.  **Use footnotes to add context** If there is a decision made around error correction that has a reasonable chance to be wrong, add a footnote to that effect.
8.  **Markdown syntax** The article should be in markdown syntax.

Here is the raw transcript data in JSON format:
{raw_transcript_data}
"""

        # Pass the prompt via stdin to the gemini-cli command. This is safer and avoids
        # shell argument length limits and complex quoting.
        process = subprocess.run(
            ["gemini"],
            input=prompt,
            capture_output=True,
            text=True,
            check=True, # Raise an exception if gemini-cli returns a non-zero exit code
            encoding='utf-8'
        )

        clean_transcript = process.stdout.strip()

        with open(clean_transcript_path, "w", encoding="utf-8") as f:
            f.write(clean_transcript)
        logging.info(f"  -> Successfully saved AI-cleaned transcript to: {clean_transcript_path}")
        return True

    except FileNotFoundError:
        logging.error("  -> AI Processing Error: 'gemini-cli' command not found.")
        logging.error("     Please ensure the Gemini CLI is installed and in your system's PATH.")
        return False
    except subprocess.CalledProcessError as e:
        logging.error("  -> AI Processing Error: The 'gemini-cli' command failed.")
        logging.error(f"     Return Code: {e.returncode}")
        logging.error(f"     Stderr: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"  -> An unexpected error occurred during AI processing: {e}")
        return False

def download_video_urls(channel_url, output_dir, redownload_video_urls=False):
    """
    Ensures the videos.json file is downloaded.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Created directory: {output_dir}")

    video_cache_path = os.path.join(output_dir, "videos.json")

    if not redownload_video_urls and os.path.exists(video_cache_path):
        logging.info(f"Found video list cache at: {video_cache_path}")
        with open(video_cache_path, 'r', encoding='utf-8') as f:
            videos = json.load(f)
        logging.info(f"Loaded {len(videos)} video details from cache.")
        return videos
    else:
        logging.info(f"Connecting to channel: {channel_url}")
        try:
            videos = list(scrapetube.get_channel(channel_url=channel_url))
            if not videos:
                logging.error("Error: Could not find any videos for this channel. Please check the URL.")
                return None
            logging.info(f"Found {len(videos)} videos. Saving video list to cache...")
            with open(video_cache_path, 'w', encoding='utf-8') as f:
                json.dump(videos, f, indent=4)
            logging.info(f"Video list saved to {video_cache_path}")
            return videos
        except Exception as e:
            logging.error(f"Error: Could not connect to the channel using scrapetube.")
            logging.error(f"Details: {e}")
            return None

def download_video_transcripts_from_urls(videos, output_dir, limit=0, force_redownload_transcripts=False, force_ai_processing=False, raw_extension="rawtranscript", processed_extension="md"):
    """
    Downloads and outputs the transcripts.
    """
    if not videos:
        return

    if limit > 0:
        logging.info(f"Limiting to the first {limit} videos.")
        videos = videos[:limit]

    ydl_opts = {'quiet': True, 'no_warnings': True}
    ydl = yt_dlp.YoutubeDL(ydl_opts)

    for i, video in enumerate(videos):
        video_id = video['videoId']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            info_dict = ydl.extract_info(video_url, download=False)
            video_title = info_dict.get('title', 'Unknown Title')
            upload_date = info_dict.get('upload_date', 'Unknown Date')
            # The string format here is YYYYMMDD. Format it to YYYY-MM-DD.
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
            
            logging.info(f"\n[{i+1}/{len(videos)}] Processing: {video_title}")
            
            safe_filename = sanitize_filename(f"{upload_date} - {video_title}")
            raw_output_path = os.path.join(output_dir, f"{safe_filename}.{raw_extension}")
            processed_output_path = os.path.join(output_dir, f"{safe_filename}.{processed_extension}")

            # --- Download Step ---
            if not os.path.exists(raw_output_path) or force_redownload_transcripts:
                try:
                    logging.info(f"  -> Downloading raw transcript for: {video_title}")
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                    
                    with open(raw_output_path, "w", encoding="utf-8") as f:
                        json.dump(transcript_list, f, indent=2)
                    logging.info(f"  -> Successfully saved raw transcript to: {raw_output_path}")

                except (NoTranscriptFound, TranscriptsDisabled):
                    logging.warning(f"  -> Skipped: No transcript found for this video.")
                    continue
                except Exception as e:
                    logging.error(f"  -> An error occurred during transcript download: {e}")
                    continue
            else:
                logging.info(f"  -> Raw transcript already exists: {raw_output_path}. Skipping download.")

            # --- AI Processing Step ---
            if not os.path.exists(raw_output_path):
                logging.warning("  -> Cannot perform AI processing because raw transcript is missing.")
                continue

            if os.path.exists(processed_output_path) and not force_ai_processing:
                logging.info(f"  -> Processed transcript already exists: {processed_output_path}. Skipping AI processing.")
                continue
            
            process_transcript_with_ai(raw_output_path, processed_output_path, video_title, video_url)

        except Exception as e:
            logging.error(f"  -> An unexpected error occurred in the main loop: {e}")

    logging.info("\n--------------------")
    logging.info("Download process finished.")
    logging.info(f"All available transcripts have been saved in the '{output_dir}' folder.")

def main():
    """
    Main function to parse arguments and start the download process.
    """
    parser = argparse.ArgumentParser(description="Download and process YouTube channel transcripts.")
    parser.add_argument("channel_url", help="The URL of the YouTube channel.")
    parser.add_argument("output_dir", help="The directory where transcripts will be saved.")
    parser.add_argument("--limit", type=int, default=0, help="Limit the number of videos to process (0 for no limit).")
    parser.add_argument("--redownload-video-urls", action="store_true", help="Force redownload of video URLs list.")
    parser.add_argument("--force-redownload-transcripts", action="store_true", help="Force redownload of raw transcripts even if they exist.")
    parser.add_argument("--force-ai-processing", action="store_true", help="Force AI processing even if the processed file exists.")
    parser.add_argument("--raw-extension", default="rawtranscript", help="Extension for raw transcript files.")
    parser.add_argument("--processed-extension", default="md", help="Extension for processed transcript files.")
    
    args = parser.parse_args()
    
    videos = download_video_urls(args.channel_url, args.output_dir, args.redownload_video_urls)
    download_video_transcripts_from_urls(
        videos,
        args.output_dir,
        limit=args.limit,
        force_redownload_transcripts=args.force_redownload_transcripts,
        force_ai_processing=args.force_ai_processing,
        raw_extension=args.raw_extension,
        processed_extension=args.processed_extension
    )

if __name__ == "__main__":
    main()

