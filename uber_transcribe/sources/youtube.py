import logging
import json
from pathlib import Path
import scrapetube
import yt_dlp
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)
from typing import List, Dict, Any, Optional

from ..models import SourceItem, SourceType

class YouTubeSource:
    """
    A source that discovers YouTube videos from a playlist and can fetch their transcripts.
    """
    def __init__(self, config: Dict[str, Any], cache_dir: Path = Path("cache/youtube")):
        """
        Initializes the source with its configuration.

        Args:
            config: A dictionary containing configuration, e.g., {"playlist_id": "..."}.
            cache_dir: The directory to store cache files.
        """
        self.playlist_id = config.get("playlist_id")
        if not self.playlist_id:
            raise ValueError("YouTubeSource config must include a 'playlist_id'.")
        
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.video_cache_path = self.cache_dir / f"{self.playlist_id}.json"
        self.raw_transcripts_dir = self.cache_dir / "raw_transcripts"
        self.raw_transcripts_dir.mkdir(parents=True, exist_ok=True)

        # Initialize yt-dlp for metadata fetching if needed
        ydl_opts = {"quiet": True, "no_warnings": True}
        self._ydl = yt_dlp.YoutubeDL(ydl_opts)

    def discover_items(self, stop_after_cache_matches=10) -> List[SourceItem]:
        """
        Fetches the list of videos from the playlist and returns them as SourceItems.
        Caches the video list to a JSON file.

        Args:
            stop_after_cache_matches: The number of consecutive known videos to see
                                      before stopping the scrape.

        Returns:
            A list of SourceItem objects.
        """
        existing_videos = []
        existing_video_ids = set()
        if self.video_cache_path.exists():
            try:
                with open(self.video_cache_path, "r", encoding="utf-8") as f:
                    existing_videos = json.load(f)
                    existing_video_ids = {v["videoId"] for v in existing_videos}
                logging.info(
                    f"Loaded {len(existing_videos)} video details from cache for playlist {self.playlist_id}."
                )
            except json.JSONDecodeError:
                logging.warning(f"Could not decode cache for {self.playlist_id}, rebuilding.")

        try:
            logging.info(f"Fetching new videos for playlist: {self.playlist_id}")
            video_generator = scrapetube.get_playlist(playlist_id=self.playlist_id)

            newly_fetched_videos = []
            for video in video_generator:
                video_id = video.get("videoId")
                if not video_id:
                    continue

                if video_id not in existing_video_ids:
                    logging.info(f"Found new video: {video_id}")
                    newly_fetched_videos.append(video)
                    existing_video_ids.add(video_id) # Add to set to handle duplicates in scrape
                else:
                    logging.info(f"Found known video: {video_id}")
                    stop_after_cache_matches -= 1
                    if stop_after_cache_matches <= 0:
                        logging.info("Stopping scrape after finding multiple known videos.")
                        break
            
            if newly_fetched_videos:
                final_video_list = newly_fetched_videos + existing_videos
                with open(self.video_cache_path, "w", encoding="utf-8") as f:
                    json.dump(final_video_list, f, indent=2)
                logging.info(
                    f"Saved {len(final_video_list)} total videos to cache for playlist {self.playlist_id}."
                )
                existing_videos = final_video_list

        except Exception as e:
            logging.exception(f"Error fetching videos from YouTube playlist {self.playlist_id}: {e}")
            # Continue with existing cache if fetching fails
        
        # Convert the raw video data into SourceItem objects
        source_items = []
        for video in existing_videos:
            item = SourceItem(
                source_id=video["videoId"], 
                source_type=SourceType.YOUTUBE_VIDEO,
                intrinsic_metadata={
                    "youtube_title": video.get("title", {}).get("runs", [{}])[0].get("text", "Unknown Title"),
                    "youtube_playlist_id": self.playlist_id
                }
            )
            source_items.append(item)
        
        logging.info(f"Discovered {len(source_items)} total items for playlist {self.playlist_id}.")
        return source_items

    def get_transcript(self, source_item: SourceItem, force_redownload: bool = False) -> Optional[Path]:
        """
        Gets the path to the transcript file for a SourceItem, downloading it if necessary.

        Args:
            source_item: The SourceItem for which to get the transcript.
            force_redownload: If True, will download the transcript even if a cached file exists.

        Returns:
            The Path to the transcript file (JSON), or None if no transcript is found.
        """
        if source_item.source_type != SourceType.YOUTUBE_VIDEO:
            return None

        video_id = source_item.source_id
        json_path = self.raw_transcripts_dir / f"{video_id}.json"
        srt_path = self.raw_transcripts_dir / f"{video_id}.srt"

        # Check for existing JSON or SRT file
        if not force_redownload:
            if json_path.exists():
                logging.info(f"Found cached raw transcript: {json_path}")
                return json_path
            if srt_path.exists():
                logging.info(f"Found cached SRT transcript: {srt_path}")
                return srt_path

        try:
            logging.info(f"Downloading raw transcript for: {video_id}")
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transcript_list, f, indent=2)
            logging.info(f"Successfully saved raw transcript to: {json_path}")
            return json_path
        except (NoTranscriptFound, TranscriptsDisabled):
            logging.warning(f"Skipped: No transcript found for video {video_id}.")
            return None
        except Exception:
            logging.exception(f"An error occurred during transcript download for {video_id}")
            return None


if __name__ == '__main__':
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)

    # This is the IMC uploads playlist ID from our config
    test_config = {"playlist_id": "UUGliqsod-tQoGiHahxS9Wig"}
    
    youtube_source = YouTubeSource(config=test_config, cache_dir=Path("uber_transcribe/cache/youtube"))
    
    # Discover items
    discovered_items = youtube_source.discover_items()

    if discovered_items:
        print(f"\nSuccessfully discovered {len(discovered_items)} items.")
        print("--- Testing Transcript Download ---")
        # Test with a known video that should have a transcript
        test_item = next((item for item in discovered_items if item.source_id == '_FEo9XSSWdU'), None)
        if test_item:
            transcript_path = youtube_source.get_transcript(test_item)
            if transcript_path and transcript_path.exists():
                print(f"Successfully got transcript for {test_item.source_id} at: {transcript_path}")
                # Clean up the downloaded file for subsequent clean test runs
                transcript_path.unlink()
            else:
                print(f"Failed to get transcript for {_FEo9XSSWdU}")
    else:
        print("No items were discovered.")

