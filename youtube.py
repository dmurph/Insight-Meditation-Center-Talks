import logging
import os
import json
import random
import scrapetube
import yt_dlp
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)
from enum import Enum
from filesystem import sanitize_filename


class UrlType(Enum):
    CHANNEL = 1
    PLAYLIST = 2


def get_video_urls(
    url_or_id,
    type: UrlType = UrlType.CHANNEL,
    rebuild_cache=False,
    skip_download=False,
):
    """
    Downloads and caches a list of video URLs from a YouTube channel or playlist.
    """
    output_dir = "cache/youtube"
    output_filename = sanitize_filename(url_or_id)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Created directory: {output_dir}")

    video_cache_path = os.path.join(output_dir, f"{output_filename}.json")

    if skip_download:
        logging.info(f"Skipping download. Using cache file: {video_cache_path}")
        if not os.path.exists(video_cache_path):
            logging.error(
                "  -> Error: --skip-video-url-download is set, but no cache file found."
            )
            return None
        try:
            with open(video_cache_path, "r", encoding="utf-8") as f:
                videos = json.load(f)
            logging.info(f"Loaded {len(videos)} video details from cache.")
            return [{"videoId": video["videoId"]} for video in videos]
        except json.JSONDecodeError as e:
            logging.error(f"  -> Error: Could not decode json from cache: {e}")
            return None

    existing_videos = []
    existing_video_ids = set()
    if not rebuild_cache and os.path.exists(video_cache_path):
        try:
            with open(video_cache_path, "r", encoding="utf-8") as f:
                existing_videos = json.load(f)
                existing_video_ids = {v["videoId"] for v in existing_videos}
            logging.info(
                f"Loaded {len(existing_videos)} video details from cache for update."
            )
        except json.JSONDecodeError as e:
            logging.warning(f"Could not decode existing cache, will rebuild: {e}")
            rebuild_cache = True

    try:
        newly_fetched_videos = []
        video_generator = None
        if type == UrlType.CHANNEL:
            logging.info(f"Connecting to channel: {url_or_id}")
            video_generator = scrapetube.get_channel(channel_url=url_or_id)
        elif type == UrlType.PLAYLIST:
            logging.info(
                f"Connecting to playlist: https://www.youtube.com/playlist?list={url_or_id}"
            )
            sleep_time = random.random() * 5
            video_generator = scrapetube.get_playlist(
                playlist_id=url_or_id, sleep=sleep_time
            )

        if not video_generator:
            logging.error("Could not create a video generator.")
            return None

        logging.info("Fetching new videos...")
        for video in video_generator:
            if not rebuild_cache and video["videoId"] in existing_video_ids:
                logging.info(f"Found existing video ({video['videoId']}), stopping.")
                break
            newly_fetched_videos.append(video)

        if not newly_fetched_videos and not existing_videos:
            logging.error("Error: Could not find any videos. Please check the argument.")
            return None

        if rebuild_cache:
            final_video_list = newly_fetched_videos
            logging.info(f"Rebuilt cache with {len(final_video_list)} videos.")
        else:
            final_video_list = newly_fetched_videos + existing_videos
            logging.info(
                f"Fetched {len(newly_fetched_videos)} new videos. Total videos: {len(final_video_list)}"
            )

        with open(video_cache_path, "w", encoding="utf-8") as f:
            json.dump(final_video_list, f, indent=4)
        logging.info(f"Video list cache saved to {video_cache_path}")

        return [{"videoId": v["videoId"]} for v in final_video_list]

    except Exception as e:
        logging.error(f"Error: Could not connect using scrapetube.")
        logging.exception(f"Details: {e}")
        return None


def get_transcript(
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
    raw_output_path = os.path.join(raw_transcripts_dir, f"{safe_filename}.json")

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
