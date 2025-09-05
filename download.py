import os
import yaml
import random
import re
import argparse
import scrapetube
import yt_dlp
import logging
import json
from enum import Enum
import subprocess
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)
import frontmatter
import download_website

logging.basicConfig(level=logging.INFO)

PROMPT_TEMPLATE = "prompt_template.mdt"


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

def add_frontmatter(
    file_string,
    youtube_title,
    youtube_url,
    date,
    speaker_name,
    speaker_url,
    talk_urls):
    post = frontmatter.loads(file_string)
    if "audiodharma_talks" in post:
        del post["audiodharma_talks"]
    post["title"] = youtube_title
    post["date"] = date
    post["video_url"] = youtube_url
    post["speaker"] = speaker_name
    post["speaker_url"] = speaker_url
    post["talk_urls"] = talk_urls
    return frontmatter.dumps(post)

def process_and_save_transcript_with_ai(
    raw_transcript_path,
    clean_transcript_path,
    youtube_title,
    youtube_url,
    date,
    speaker_name,
    speaker_url,
    talk_urls,
    talk_headers,
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
        return "no_transcript"
    if os.path.exists(clean_transcript_path) and not force_ai_processing:
        with open(clean_transcript_path, "r", encoding="utf-8") as f:
            clean_transcript = f.read()
        with_frontmatter = add_frontmatter(
            clean_transcript,
            youtube_title,
            youtube_url,
            date,
            speaker_name,
            speaker_url,
            talk_urls,
        )
        if with_frontmatter != clean_transcript:
            logging.info(
                f"  -> Updating frontmatter for {clean_transcript_path}. Skipping AI processing."
            )
            with open(clean_transcript_path, "w", encoding="utf-8") as f:
                f.write(with_frontmatter)
            return "updated_frontmatter"
        else:
            logging.info(
                f"  -> Processed transcript already exists: {clean_transcript_path}. Skipping AI processing."
            )
            return "already_processed"
    transcript_extension = raw_transcript_path.split(".")[-1]

    try:
        with open(PROMPT_TEMPLATE, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logging.error("  -> Could not find prompt template file!")
        return "error"

    try:
        with open(raw_transcript_path, "r", encoding="utf-8") as f:
            raw_transcript_data = f.read()

        prompt = prompt_template
        # Replace top-level placeholders first
        prompt = prompt.replace("{video_title}", youtube_title)
        prompt = prompt.replace("{video_url}", youtube_url)

        # Replace new placeholders
        prompt = prompt.replace("{speaker_name}", speaker_name)
        prompt = prompt.replace("{speaker_url}", speaker_url)
        prompt = prompt.replace("{talk_headers}", talk_headers)
        prompt = prompt.replace("{transcript_extension}", transcript_extension)
        prompt = prompt.replace("{raw_transcript_data}", raw_transcript_data)

        # Pass the prompt via stdin to the gemini-cli command.
        process = subprocess.run(
            ["gemini"],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )

        clean_transcript = process.stdout.strip()

        # Remove markdown block fences
        lines = clean_transcript.split('\n')
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        clean_transcript = '\n'.join(lines)

        final_content = add_frontmatter(
            clean_transcript,
            youtube_title,
            youtube_url,
            date,
            speaker_name,
            speaker_url,
            talk_urls,
        )

        with open(clean_transcript_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        logging.info(
            f"  -> Successfully saved AI-cleaned transcript to: {clean_transcript_path}"
        )
        return "ai_processed"
    except FileNotFoundError:
        logging.error("  -> AI Processing Error: 'gemini-cli' command not found.")
        logging.error(
            "     Please ensure the Gemini CLI is installed and in your system's PATH."
        )
        return "error"
    except subprocess.CalledProcessError as e:
        logging.error("  -> AI Processing Error: The 'gemini-cli' command failed.")
        logging.error(f"     Return Code: {e.returncode}")
        logging.error(f"     Stderr: {e.stderr}")
        return "error"
    except Exception as e:
        logging.error(f"  -> An unexpected error occurred during AI processing: {e}")
        return "error"

class UrlType(Enum):
    CHANNEL = 1
    PLAYLIST = 2

def download_video_urls(
    url_or_id,
    type: UrlType = UrlType.CHANNEL,
    rebuild_cache=False,
    skip_download=False,
):
    """
    Downloads and caches a list of video URLs from a YouTube channel or playlist.

    The function supports several modes of operation:
    - skip_download: Only use the cached list of video URLs, without making any network requests.
    - rebuild_cache: Force a complete redownload of all video URLs, overwriting the existing cache.
    - Default (efficient update): Download new video URLs until an already cached video is found.
      This updates the cache with the latest videos without re-downloading the entire list.
    """
    output_dir = "cache/youtube"
    output_filename = sanitize_filename(url_or_id)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Created directory: {output_dir}")

    video_cache_path = os.path.join(output_dir, f"{output_filename}.json")

    # --- Behavior 1: Skip Download and Use Cache ---
    if skip_download:
        logging.info(f"Skipping download. Using cache file: {video_cache_path}")
        if not os.path.exists(video_cache_path):
            logging.error("  -> Error: --skip-video-url-download is set, but no cache file found.")
            return None
        try:
            with open(video_cache_path, "r", encoding="utf-8") as f:
                videos = json.load(f)
            logging.info(f"Loaded {len(videos)} video details from cache.")
            return [{"videoId": video["videoId"]} for video in videos]
        except json.JSONDecodeError as e:
            logging.error(f"  -> Error: Could not decode json from cache: {e}")
            return None

    # --- Load Existing Cache for Update or Rebuild ---
    existing_videos = []
    existing_video_ids = set()
    if not rebuild_cache and os.path.exists(video_cache_path):
        try:
            with open(video_cache_path, "r", encoding="utf-8") as f:
                existing_videos = json.load(f)
                existing_video_ids = {v["videoId"] for v in existing_videos}
            logging.info(f"Loaded {len(existing_videos)} video details from cache for update.")
        except json.JSONDecodeError as e:
            logging.warning(f"Could not decode existing cache, will rebuild: {e}")
            rebuild_cache = True # Force rebuild if cache is corrupt

    # --- Behavior 2: Rebuild Cache or Perform Efficient Update ---
    try:
        newly_fetched_videos = []
        stop_fetching = False

        # Determine the generator based on the URL type
        video_generator = None
        if type == UrlType.CHANNEL:
            logging.info(f"Connecting to channel: {url_or_id}")
            video_generator = scrapetube.get_channel(channel_url=url_or_id)
        elif type == UrlType.PLAYLIST:
            logging.info(f"Connecting to playlist: https://www.youtube.com/playlist?list={url_or_id}")
            sleep_time = random.random() * 5
            video_generator = scrapetube.get_playlist(playlist_id=url_or_id, sleep=sleep_time)

        if not video_generator:
            logging.error("Could not create a video generator.")
            return None

        logging.info("Fetching new videos...")
        for video in video_generator:
            if not rebuild_cache and video["videoId"] in existing_video_ids:
                logging.info(f"Found existing video ({video['videoId']}), stopping.")
                stop_fetching = True
                break
            newly_fetched_videos.append(video)

        if not newly_fetched_videos and not existing_videos:
            logging.error("Error: Could not find any videos. Please check the argument.")
            return None

        # --- Combine and Save Cache ---
        if rebuild_cache:
            final_video_list = newly_fetched_videos
            logging.info(f"Rebuilt cache with {len(final_video_list)} videos.")
        else:
            final_video_list = newly_fetched_videos + existing_videos
            logging.info(f"Fetched {len(newly_fetched_videos)} new videos. Total videos: {len(final_video_list)}")

        with open(video_cache_path, "w", encoding="utf-8") as f:
            json.dump(final_video_list, f, indent=4)
        logging.info(f"Video list cache saved to {video_cache_path}")

        return [{"videoId": v["videoId"]} for v in final_video_list]

    except Exception as e:
        logging.error(f"Error: Could not connect using scrapetube.")
        logging.exception(f"Details: {e}")
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
    raw_transcripts_dir = "cache/raw_transcripts"
    if not os.path.exists(raw_transcripts_dir):
        os.makedirs(raw_transcripts_dir)

    safe_filename = sanitize_filename(f"{upload_date} - {video_title}")
    srt_path = os.path.join(raw_transcripts_dir, f"{safe_filename}.srt")
    raw_output_path = os.path.join(
        raw_transcripts_dir, f"{safe_filename}.json"
    )

    if os.path.exists(srt_path) and not force_redownload_transcripts:
        logging.info(f"  -> Found local SRT file: {srt_path}")
        return srt_path

    if os.path.exists(raw_output_path) and not force_redownload_transcripts:
        logging.info(f"  -> Found local raw transcript file: {raw_output_path}")
        return raw_output_path

    try:
        logging.info(f"  -> Downloading raw transcript for: {video_title}")
        transcript_list = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en"]
        )

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
    do_not_stop_scan=False,
):
    """
    Downloads and outputs the transcripts.
    """
    if not videos:
        return

    if limit > 0:
        logging.info(f"Limiting to the first {limit} videos.")
        videos = videos[:limit]

    # Load audiodharma data
    try:
        with open("cache/audiodharma/talks.yaml", "r", encoding="utf-8") as f:
            audiodharma_talks_data = yaml.safe_load(f)
        with open("cache/audiodharma/speakers.yaml", "r", encoding="utf-8") as f:
            speakers_data = yaml.safe_load(f)

        # Create a mapping from youtube_id to talks
        audiodharma_talks_map = {
            item["youtube_id"]: item["talks"] for item in audiodharma_talks_data
        }

    except FileNotFoundError as e:
        logging.warning(f"Could not load audiodharma data: {e}. Continuing without it.")
        audiodharma_talks_map = {}
        speakers_data = {}

    ydl_opts = {"quiet": True, "no_warnings": True}
    ydl = yt_dlp.YoutubeDL(ydl_opts)

    metadata_cache_path = "cache/youtube/video_metadata_cache.json"
    if os.path.exists(metadata_cache_path):
        with open(metadata_cache_path, "r", encoding="utf-8") as f:
            metadata_cache = json.load(f)
    else:
        metadata_cache = {}

    for i, video in enumerate(videos):
        video_id = video["videoId"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            metadata = get_video_metadata(
                video_id, video_url, ydl, metadata_cache, skip_metadata_cache
            )
            video_title = metadata["title"]
            upload_date = metadata["upload_date"]

            with open(metadata_cache_path, "w", encoding="utf-8") as f:
                json.dump(metadata_cache, f, indent=4)

            logging.info(f"\n[{i+1}/{len(videos)}] Processing: {video_title}")

            # Get audiodharma info
            speaker_name = "Unknown"
            speaker_url = ""
            talk_urls = []
            talk_headers_str = ""

            if video_id in audiodharma_talks_map:
                talks = audiodharma_talks_map[video_id]
                if not talks:
                    logging.warning(f"  -> No talks found for video ID: {video_id}")
                    break;
                # Get speaker from the first talk
                speaker_id = talks[0].get("speaker_id")
                if speaker_id and speaker_id in speakers_data:
                    speaker_info = speakers_data[speaker_id]
                    speaker_name = speaker_info.get("name", "Unknown")
                    speaker_url = speaker_info.get("url", "")
                else:
                    logging.warning(f"  -> No speaker found for speaker ID: {speaker_id}")

                # Format talks for prompt
                formatted_talks = []
                talk_headers = []
                for talk in talks:
                    talk_id = talk.get("id")
                    talk_title = talk.get("title")
                    if not talk_id and not talk_title:
                        logging.warning(f"No talk on audiodharma yet for video {video_id}")
                        break;
                    talk_urls.append(
                        f"https://www.audiodharma.org/talks/{talk_id}"
                    )
                    talk_headers.append(
                        f"      `## {talk_title} ([link](https://www.audiodharma.org/talks/{talk_id}))`"
                    )
                talk_headers_str = "\n".join(talk_headers)

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
                result = process_and_save_transcript_with_ai(
                    raw_transcript_path,
                    processed_output_path,
                    video_title,
                    video_url,
                    upload_date,
                    speaker_name,
                    speaker_url,
                    talk_urls,
                    talk_headers_str,
                    force_ai_processing,
                )
                if result == "error":
                    break
                if result == "already_processed" and not do_not_stop_scan:
                    logging.info(
                        f"  -> Already processed and up-to-date. Stopping scan (specify --do-not-stop-scan to scan for all videos)."
                    )
                    break

        except Exception as e:
            logging.error(f"  -> An unexpected error occurred in the main loop: {e}")

    logging.info("\n--------------------")
    logging.info("Download process finished.")
    logging.info(
        f"All available transcripts have been saved in the raw_transcripts folder."
    )


def main():
    """
    Main function to parse arguments and start the download process.
    """
    logging.info("Running website download script first...")
    download_website.run_scraper()
    logging.info("Finished running website download script.")

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
        "url", help="The URL of the YouTube channel. Defaults to the IMC live stream channel", type=str, default="https://www.youtube.com/@InsightMeditationCenter/streams"
    )
    channel_url_source.add_argument(
        "--rebuild-video-url-cache",
        action="store_true",
        help="Force a complete redownload of all video URLs, rebuilding the cache.",
    )
    channel_url_source.add_argument(
        "--skip-video-url-download",
        action="store_true",
        help="Skip downloading video URLs and use the existing cache.",
    )

    playlist_url_source = sources.add_parser("playlist-id", help="Use a playlist id")
    playlist_url_source.add_argument(
        "playlist_id", help="The id of a YouTube playlist. Defaults to all videos on the IMC channel.", type=str, default="UUGliqsod-tQoGiHahxS9Wig"
    )
    playlist_url_source.add_argument(
        '--rebuild-video-url-cache',
        action='store_true',
        help='Force a complete redownload of all video URLs, rebuilding the cache.')
    playlist_url_source.add_argument(
        "--skip-video-url-download",
        action="store_true",
        help="Skip downloading video URLs and use the existing cache.",
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
    parser.add_argument(
        "--do-not-stop-scan",
        action="store_true",
        help="Don't stop processing the videos if a talk was already found as saved with the correct metadata, keep going for all videos in the playlist/channel/etc.",
    )

    args = parser.parse_args()

    # Consolidate cache-related arguments from subparsers
    rebuild_cache = getattr(args, 'rebuild_video_url_cache', False)
    skip_download = getattr(args, 'skip_video_url_download', False)

    if args.fetch_source == "video-id":
        videos = [{"videoId": args.id}]
    elif args.fetch_source == "channel-url":
        videos = download_video_urls(
            url_or_id=args.url,
            type=UrlType.CHANNEL,
            rebuild_cache=rebuild_cache,
            skip_download=skip_download,
        )
    elif args.fetch_source == "playlist-id":
        videos = download_video_urls(
            url_or_id=args.playlist_id,
            type=UrlType.PLAYLIST,
            rebuild_cache=rebuild_cache,
            skip_download=skip_download,
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
        do_not_stop_scan=args.do_not_stop_scan,
    )


if __name__ == "__main__":
    main()
