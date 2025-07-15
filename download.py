import os
import re
import argparse
import scrapetube
import yt_dlp
import logging
import json
import subprocess
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)

logging.basicConfig(level=logging.INFO)

RAW_EXTENSION = "rawtranscript"
PROMPT_TEMPLATE = "prompt_template.md"


def sanitize_filename(title):
    """
    Removes characters that are illegal in file names across different OS.
    """
    # Change / to - for some ok structure.
    sanitized = re.sub(r"[\\/]", "-", title)
    # Remove illegal characters
    sanitized = re.sub(r'[\\/*?:"<>|]', "", sanitized)
    # Replace sequences of whitespace with a single space
    sanitized = re.sub(r"\\s+", " ", sanitized)
    # Trim leading/trailing whitespace
    return sanitized.strip()


def process_and_save_transcript_with_ai(
    raw_transcript_path,
    clean_transcript_path,
    video_title,
    video_url,
    force_ai_processing=False,
):
    """
    Processes a raw transcript file using gemini-cli to produce a clean version.
    """

    logging.info(f"  -> Processing with AI: {raw_transcript_path}")
    if not os.path.exists(raw_transcript_path):
        logging.warning(
            "  -> Cannot perform AI processing because raw transcript is missing."
        )
    if os.path.exists(clean_transcript_path) and not force_ai_processing:
        logging.info(
            f"  -> Processed transcript already exists: {clean_transcript_path}. Skipping AI processing."
        )
        return
    transcript_extension = raw_transcript_path.split(".")[-1]

    try:
        with open(PROMPT_TEMPLATE, "r", encoding="utf-8") as f:
            prompt_template = f.read() 
    except FileNotFoundError:
        logging.error("  -> Could not find prompt template file!");
        return False;

    try:
        with open(raw_transcript_path, "r", encoding="utf-8") as f:
            raw_transcript_data = f.read()

        
        # The template expects the following to be replaced:
        # - {video_title}
        # - {video_url}
        # - {transcript_extension}
        # - {raw_transcript_data}
        prompt = prompt_template.replace("{transcript_extension}", transcript_extension);
        prompt = prompt.replace("{video_title}", video_title);
        prompt = prompt.replace("{video_url}", video_url);
        prompt = prompt.replace("{raw_transcript_data}", raw_transcript_data);
    

        # Pass the prompt via stdin to the gemini-cli command. This is safer and avoids
        # shell argument length limits and complex quoting.
        process = subprocess.run(
            ["gemini"],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,  # Raise an exception if gemini-cli returns a non-zero exit code
            encoding="utf-8",
        )

        clean_transcript = process.stdout.strip()

        with open(clean_transcript_path, "w", encoding="utf-8") as f:
            f.write(clean_transcript)
        logging.info(
            f"  -> Successfully saved AI-cleaned transcript to: {clean_transcript_path}"
        )
        return True

    except FileNotFoundError:
        logging.error("  -> AI Processing Error: 'gemini-cli' command not found.")
        logging.error(
            "     Please ensure the Gemini CLI is installed and in your system's PATH."
        )
        return False
    except subprocess.CalledProcessError as e:
        logging.error("  -> AI Processing Error: The 'gemini-cli' command failed.")
        logging.error(f"     Return Code: {e.returncode}")
        logging.error(f"     Stderr: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"  -> An unexpected error occurred during AI processing: {e}")
        return False


def download_video_urls(channel_url, output_filename, redownload_video_urls=False):
    """
    Ensures the videos.json file is downloaded.
    """
    output_dir = "videos"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Created directory: {output_dir}")

    video_cache_path = os.path.join(output_dir, f"{output_filename}.json")
    logging.info(f"Saving to {video_cache_path}")

    if not redownload_video_urls and os.path.exists(video_cache_path):
        logging.info(f"Found video list cache at: {video_cache_path}")
        with open(video_cache_path, "r", encoding="utf-8") as f:
            videos = json.load(f)
        logging.info(f"Loaded {len(videos)} video details from cache.")
        # Prune the video data to only include videoId
        return [{"videoId": video["videoId"]} for video in videos]

    logging.info(f"Connecting to channel: {channel_url}")
    try:
        videos_full = list(scrapetube.get_channel(channel_url=channel_url))
        if not videos_full:
            logging.error(
                "Error: Could not find any videos for this channel. Please check the URL."
            )
            return None

        logging.info(f"Found {len(videos_full)} videos. Saving video list to cache...")
        with open(video_cache_path, "w", encoding="utf-8") as f:
            json.dump(videos_full, f, indent=4)
        logging.info(f"Video list saved to {video_cache_path}")

        # Prune the video data to only include videoId
        return [{"videoId": video["videoId"]} for video in videos_full]
    except Exception as e:
        logging.error(f"Error: Could not connect to the channel using scrapetube.")
        logging.error(f"Details: {e}")
        return None


def download_or_use_transcript(
    video_id,
    video_title,
    upload_date,
    force_redownload_transcripts,
):
    """
    Gets the path to the transcript file, downloading it if necessary.
    First, it looks for a local SRT file.
    """
    raw_transcripts_dir = "raw_transcripts"
    if not os.path.exists(raw_transcripts_dir):
        os.makedirs(raw_transcripts_dir)

    safe_filename = sanitize_filename(f"{upload_date} - {video_title}")
    srt_path = os.path.join(raw_transcripts_dir, f"{safe_filename}.srt")
    raw_output_path = os.path.join(
        raw_transcripts_dir, f"{safe_filename}.{RAW_EXTENSION}"
    )

    if os.path.exists(srt_path) and not force_redownload_transcripts:
        logging.info(f"  -> Found local SRT file: {srt_path}")
        return srt_path

    if os.path.exists(raw_output_path) and not force_redownload_transcripts:
        logging.info(f"  -> Found local raw transcript file: {raw_output_path}")
        return raw_output_path

    try:
        logging.info(f"  -> Downloading raw transcript for: {video_title}")
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(transcript_list, f, indent=2)
        logging.info(f"  -> Successfully saved raw transcript to: {raw_output_path}")
        return raw_output_path
    except (NoTranscriptFound, TranscriptsDisabled):
        logging.warning(f"  -> Skipped: No transcript found for this video.")
        return None
    except Exception as e:
        logging.error(f"  -> An error occurred during transcript download: {e}")
        return None


def get_video_metadata(video_id, video_url, ydl, metadata_cache, skip_metadata_cache):
    if not skip_metadata_cache and video_id in metadata_cache:
        logging.info(f"  -> Found metadata in cache for video ID: {video_id}")
        return metadata_cache[video_id]

    logging.info(f"  -> Fetching metadata from YouTube for video ID: {video_id}")
    info_dict = ydl.extract_info(video_url, download=False)
    video_title = info_dict.get("title", "Unknown Title")
    upload_date = info_dict.get("upload_date", "Unknown Date")
    # The string format here is YYYYMMDD. Format it to YYYY-MM-DD.
    upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    
    metadata = {
        "title": video_title,
        "upload_date": upload_date,
    }
    metadata_cache[video_id] = metadata
    return metadata

def download_video_transcripts_from_urls(
    videos,
    limit=0,
    force_redownload_transcripts=False,
    force_ai_processing=False,
    skip_metadata_cache=False,
):
    """
    Downloads and outputs the transcripts.
    """
    if not videos:
        return

    if limit > 0:
        logging.info(f"Limiting to the first {limit} videos.")
        videos = videos[:limit]

    ydl_opts = {"quiet": True, "no_warnings": True}
    ydl = yt_dlp.YoutubeDL(ydl_opts)

    metadata_cache_path = "videos/video_metadata_cache.json"
    if os.path.exists(metadata_cache_path):
        with open(metadata_cache_path, "r", encoding="utf-8") as f:
            metadata_cache = json.load(f)
    else:
        metadata_cache = {}

    for i, video in enumerate(videos):
        video_id = video["videoId"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            metadata = get_video_metadata(video_id, video_url, ydl, metadata_cache, skip_metadata_cache)
            video_title = metadata["title"]
            upload_date = metadata["upload_date"]

            logging.info(f"\n[{i+1}/{len(videos)}] Processing: {video_title}")

            raw_transcript_path = download_or_use_transcript(
                video_id,
                video_title,
                upload_date,
                force_redownload_transcripts,
            )

            if raw_transcript_path:
                talks_dir = "talks"
                if not os.path.exists(talks_dir):
                    os.makedirs(talks_dir)
                safe_filename = sanitize_filename(f"{upload_date} - {video_title}")
                processed_output_path = os.path.join(talks_dir, f"{safe_filename}.md")
                process_and_save_transcript_with_ai(
                    raw_transcript_path,
                    processed_output_path,
                    video_title,
                    video_url,
                    force_ai_processing,
                )

        except Exception as e:
            logging.error(f"  -> An unexpected error occurred in the main loop: {e}")

    with open(metadata_cache_path, "w", encoding="utf-8") as f:
        json.dump(metadata_cache, f, indent=4)

    logging.info("\n--------------------")
    logging.info("Download process finished.")
    logging.info(
        f"All available transcripts have been saved in the raw_transcripts folder."
    )


def main():
    """
    Main function to parse arguments and start the download process.
    """
    parser = argparse.ArgumentParser(
        description="Download and process YouTube channel transcripts."
    )
    sources = parser.add_subparsers(
        dest="fetch_source", help="Specify the type of source to fetch", required=True
    )
    video_id_source = sources.add_parser("video-id", help="Use a video id by itself")
    video_id_source.add_argument(
        "id",
        help="The ID of a single YouTube video to process.",
        type=str,
    )

    channel_url_source = sources.add_parser("channel-url", help="Use a channel url")
    channel_url_source.add_argument(
        "url", help="The URL of the YouTube channel.", type=str
    )
    channel_url_source.add_argument(
        "--redownload-video-urls",
        action="store_true",
        help="Force redownload of video URLs list.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit the number of videos to process (0 for no limit).",
    )
    parser.add_argument(
        "--force-redownload-transcripts",
        action="store_true",
        help="Force redownload of raw transcripts even if they exist.",
    )
    parser.add_argument(
        "--force-ai-processing",
        action="store_true",
        help="Force AI processing even if the processed file exists.",
    )
    parser.add_argument(
        "--skip-metadata-cache",
        action="store_true",
        help="Skip using the metadata cache and force re-fetching from YouTube.",
    )

    args = parser.parse_args()

    if args.fetch_source == "video-id":
        videos = [{"videoId": args.id}]
    elif args.fetch_source == "channel-url":
        videos = download_video_urls(
            args.url,
            sanitize_filename(args.url),
            args.redownload_video_urls,
        )
    else:
        parser.print_help()
        return

    if not videos:
        logging.info("No videos found. Exiting.")
        return

    download_video_transcripts_from_urls(
        videos,
        limit=args.limit,
        force_redownload_transcripts=args.force_redownload_transcripts,
        force_ai_processing=args.force_ai_processing,
        skip_metadata_cache=args.skip_metadata_cache,
    )


if __name__ == "__main__":
    main()
