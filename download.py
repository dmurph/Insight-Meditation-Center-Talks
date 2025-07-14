import os
import re
import argparse
import scrapetube
import yt_dlp
import logging
import json
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

def download_video_transcripts_from_urls(videos, output_dir, limit=0, force_redownload_transcripts=False):
    """
    Downloads and outputs the transcripts.
    """
    if not videos:
        return

    if limit > 0 and len(videos) > limit:
        logging.info(f"Limiting to {limit} videos.")
        videos = videos[:limit]

    ydl_opts = {'quiet': True, 'no_warnings': True}
    ydl = yt_dlp.YoutubeDL(ydl_opts)

    for i, video in enumerate(videos):
        video_id = video['videoId']
        try:
            info_dict = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            video_title = info_dict.get('title', 'Unknown Title')
            upload_date = info_dict.get('upload_date', 'Unknown Date')
            # The string format here is YYYYMMDD. Format it to YYYY-MM-DD.
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
            
            logging.info(f"\n[{i+1}/{len(videos)}] Processing: {video_title}")
            
            safe_filename = sanitize_filename(f"{upload_date} - {video_title}");
            output_path = os.path.join(output_dir, safe_filename + ".txt")

            if os.path.exists(output_path) and not force_redownload_transcripts:
                logging.info(f"  -> Transcript already exists at: {output_path}. Skipping.")
                continue

            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            # First, save the raw transcription to a .rawtranscript file
            raw_output_path = os.path.join(output_dir, safe_filename + ".rawtranscript")
            with open(raw_output_path, "w", encoding="utf-8") as f:
                json.dump(transcript_list, f, indent=2)
                logging.info(f"  -> Successfully saved raw transcript to: {raw_output_path}")

            with open(output_path, "w", encoding="utf-8") as f:
                full_transcript = " ".join([item['text'] for item in transcript_list])
                f.write(full_transcript)
            
            logging.info(f"  -> Successfully saved transcript to: {output_path}")

        except NoTranscriptFound:
            logging.warning(f"  -> Skipped: No transcript found for this video.")
        except TranscriptsDisabled:
            logging.warning(f"  -> Skipped: Transcripts are disabled for this video.")
        except Exception as e:
            logging.error(f"  -> An unexpected error occurred: {e}")

    logging.info("\n--------------------")
    logging.info("Download process finished.")
    logging.info(f"All available transcripts have been saved in the '{output_dir}' folder.")

def main():
    """
    Main function to parse arguments and start the download process.
    """
    parser = argparse.ArgumentParser(description="Download YouTube channel transcripts.")
    parser.add_argument("channel_url", help="The URL of the YouTube channel.")
    parser.add_argument("output_dir", help="The directory where transcripts will be saved.")
    parser.add_argument("--limit", type=int, default=0, help="Limit the number of videos to download (0 for no limit).")
    parser.add_argument("--redownload-video-urls", action="store_true", help="Force redownload of video URLs list.")
    parser.add_argument("--force-redownload-transcripts", action="store_true", help="Force redownload of transcripts even if they exist.")
    
    args = parser.parse_args()
    
    videos = download_video_urls(args.channel_url, args.output_dir, args.redownload_video_urls)
    download_video_transcripts_from_urls(videos, args.output_dir, args.limit, args.force_redownload_transcripts)

if __name__ == "__main__":
    main()
