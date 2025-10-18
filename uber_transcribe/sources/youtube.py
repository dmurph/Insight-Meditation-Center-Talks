import logging
import json
from pathlib import Path
import scrapetube
from typing import List, Dict, Any

from ..models import SourceItem, SourceType

class YouTubeSource:
    """
    A source that discovers YouTube videos from a playlist.
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
        source_items = [
            SourceItem(source_id=video["videoId"], source_type=SourceType.YOUTUBE_VIDEO)
            for video in existing_videos
        ]
        
        logging.info(f"Discovered {len(source_items)} total items for playlist {self.playlist_id}.")
        return source_items

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
        print("Here are the first 5:")
        for item in discovered_items[:5]:
            print(f"  - ID: {item.source_id}, Type: {item.source_type.value}")
    else:
        print("No items were discovered.")

