import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ..models import SourceItem, SourceType

class AudioDharmaProvider:
    """
    A MetadataProvider that enriches SourceItems with data scraped from audiodharma.org.
    """
    def __init__(self, cache_dir: Path = Path("cache/audiodharma")):
        """
        Initializes the provider and loads the audiodharma data from the cache.

        Args:
            cache_dir: The directory where the audiodharma YAML cache files are stored.
        """
        self.cache_dir = cache_dir
        self._talks_map: Dict[str, Any] = {}
        self._speakers_map: Dict[int, Any] = {}
        self._load_data_from_cache()

    def _load_data_from_cache(self):
        """Loads the talks and speakers data from the YAML cache files."""
        talks_path = self.cache_dir / "talks.yaml"
        speakers_path = self.cache_dir / "speakers.yaml"

        if not talks_path.exists() or not speakers_path.exists():
            logging.warning(
                f"AudioDharma cache files not found in {self.cache_dir}. "
                "Provider will not have any data."
            )
            return

        try:
            with open(talks_path, "r", encoding="utf-8") as f:
                audiodharma_talks_data = yaml.safe_load(f)
                if audiodharma_talks_data:
                    self._talks_map = {
                        item["youtube_id"]: item["talks"] for item in audiodharma_talks_data
                    }

            with open(speakers_path, "r", encoding="utf-8") as f:
                speakers_data = yaml.safe_load(f)
                if speakers_data:
                    # Ensure keys are integers
                    self._speakers_map = {int(k): v for k, v in speakers_data.items()}
            
            logging.info(
                f"Successfully loaded AudioDharma cache with {len(self._talks_map)} videos "
                f"and {len(self._speakers_map)} speakers."
            )

        except Exception as e:
            logging.exception(f"Error loading AudioDharma cache: {e}")

    def bulk_load_data(self):
        """
        Ensures the data is loaded from the cache. In a future implementation,
        this method would trigger the live scraping logic if the cache is stale.
        For now, it does nothing as the constructor already loads the data.
        """
        logging.info("AudioDharmaProvider: `bulk_load_data` called. "
                     "Currently relying on existing cache.")
        if not self._talks_map or not self._speakers_map:
            self._load_data_from_cache()


    def lookup(self, source_item: SourceItem) -> Optional[Dict[str, Any]]:
        """
        Looks up a SourceItem and returns supplemental metadata if a match is found.

        Args:
            source_item: The SourceItem to enrich.

        Returns:
            A dictionary of supplemental metadata, or None if no match is found.
        """
        if source_item.source_type != SourceType.YOUTUBE_VIDEO:
            return None

        video_id = source_item.source_id
        if video_id not in self._talks_map:
            return None

        talks = self._talks_map[video_id]
        if not talks:
            return None

        # Use the first talk to determine the primary speaker
        primary_talk = talks[0]
        speaker_id = primary_talk.get("speaker_id")
        
        speaker_name = "Unknown"
        speaker_url = ""
        if speaker_id and speaker_id in self._speakers_map:
            speaker_info = self._speakers_map[speaker_id]
            speaker_name = speaker_info.get("name", "Unknown")
            speaker_url = speaker_info.get("url", "")

        # Aggregate all talk URLs for this video
        talk_urls = [
            f"https://www.audiodharma.org/talks/{talk.get('id')}"
            for talk in talks if talk.get('id')
        ]

        return {
            "speaker_name": speaker_name,
            "speaker_url": speaker_url,
            "audiodharma_speaker_id": speaker_id,
            "audiodharma_talks": talks,
            "audiodharma_urls": talk_urls,
        }

if __name__ == '__main__':
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    # Create a dummy SourceItem for a known video
    test_video_id = "_FEo9XSSWdU" # A known video ID from the cache
    item_to_test = SourceItem(source_id=test_video_id, source_type=SourceType.YOUTUBE_VIDEO)

    # Initialize the provider from the new cache location
    provider = AudioDharmaProvider(cache_dir=Path("uber_transcribe/cache/audiodharma"))
    
    # Perform the lookup
    metadata = provider.lookup(item_to_test)

    if metadata:
        print(f"Successfully found metadata for video {test_video_id}:")
        import json
        print(json.dumps(metadata, indent=2))
    else:
        print(f"Could not find metadata for video {test_video_id}.")

