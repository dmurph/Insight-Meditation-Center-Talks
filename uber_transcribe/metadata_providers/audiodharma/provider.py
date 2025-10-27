import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict

import requests

from uber_transcribe.models import SourceItem, SourceType
from .models import AudioDharmaTalk, AudioDharmaSpeaker
from uber_transcribe.metadata_providers.audiodharma.scraper import AudioDharmaScraper


class AudioDharmaProvider:
    """
    Provides metadata for talks from audiodharma.org, managing scraping and caching.
    """

    def __init__(self, cache_dir: Path = Path("cache/audiodharma")):
        self.cache_dir = cache_dir
        self.scraper = AudioDharmaScraper()
        self._talks_by_id: Dict[int, AudioDharmaTalk] = {}
        self._speakers_by_id: Dict[int, AudioDharmaSpeaker] = {}
        self._talks_by_youtube_id: Dict[str, List[AudioDharmaTalk]] = defaultdict(list)

    def _load_data_from_cache(self):
        """Loads the talks and speakers data from the JSON cache files."""
        # Clear existing in-memory data to ensure a fresh load
        self._talks_by_id.clear()
        self._speakers_by_id.clear()
        self._talks_by_youtube_id.clear()

        talks_path = self.cache_dir / "talks.json"
        speakers_path = self.cache_dir / "speakers.json"

        if not talks_path.exists() or not speakers_path.exists():
            return

        try:
            with open(talks_path, "r", encoding="utf-8") as f:
                talks_data = json.load(f)
                for talk_id_str, talk_dict in talks_data.items():
                    talk_id = int(talk_id_str)
                    talk_dict["id"] = talk_id
                    talk = AudioDharmaTalk.model_validate(talk_dict)
                    self._talks_by_id[talk.id] = talk
                    if talk.youtube_id:
                        self._talks_by_youtube_id[talk.youtube_id].append(talk)

            with open(speakers_path, "r", encoding="utf-8") as f:
                speakers_data = json.load(f)
                for speaker_id_str, speaker_dict in speakers_data.items():
                    speaker_id = int(speaker_id_str)
                    speaker_dict["id"] = speaker_id
                    speaker = AudioDharmaSpeaker.model_validate(speaker_dict)
                    self._speakers_by_id[speaker.id] = speaker
            logging.info(
                f"Loaded {len(self._talks_by_id)} talks and {len(self._speakers_by_id)} speakers from cache."
            )
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Error loading data from cache: {e}")

    def bulk_load_data(self):
        self._load_data_from_cache()
        self.update_cache()

    def update_cache(self, pages_to_scan: int = 2, html_content: Optional[str] = None) -> Tuple[Dict[int, AudioDharmaTalk], Dict[int, AudioDharmaSpeaker]]:
        """
        Fetches the latest talks from audiodharma.org and updates the local cache.
        
        Returns the scraped talks and speakers.
        """
        logging.info("Updating AudioDharma cache...")
        
        # For now, we'll just use the provided HTML content for testing
        if html_content:
            self._load_data_from_cache()
            talks, speakers = self.scraper.parse_page(html_content, self._speakers_by_id)
            self._save_cache(talks, speakers)
            self._load_data_from_cache()
            return self._talks_by_id, self._speakers_by_id

        # In a real scenario, you would loop through pages here
        # For this refactor, we'll keep it simple and assume a single page for now.
        # url = "https://www.audiodharma.org/talks"
        # response = requests.get(url)
        # talks, speakers = self.scraper.parse_page(response.text)
        # self._save_cache(talks, speakers)
        # self._load_data_from_cache()
        return {}, {}

    def _save_cache(self, talks: Dict[int, AudioDharmaTalk], speakers: Dict[int, AudioDharmaSpeaker]):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        talks_path = self.cache_dir / "talks.json"
        speakers_path = self.cache_dir / "speakers.json"

        # Create lean dictionaries for JSON storage
        talks_to_save = {
            talk.id: talk.model_dump(exclude={'id'}) for talk in talks.values()
        }
        speakers_to_save = {
            speaker.id: speaker.model_dump(exclude={'id'}) for speaker in speakers.values()
        }

        with open(talks_path, "w", encoding="utf-8") as f:
            json.dump(talks_to_save, f, indent=2, sort_keys=True)
        with open(speakers_path, "w", encoding="utf-8") as f:
            json.dump(speakers_to_save, f, indent=2, sort_keys=True)
        logging.info(f"Saved {len(talks)} talks and {len(speakers)} speakers to cache.")

    def lookup(self, source_item: SourceItem) -> Optional[Dict[str, Any]]:
        if source_item.source_type != SourceType.YOUTUBE_VIDEO:
            return None
        talks = self._talks_by_youtube_id.get(source_item.source_id)
        if not talks:
            return None
        primary_talk = talks[0]
        
        speaker_names = []
        speaker_urls = []
        for speaker_id in primary_talk.speaker_ids:
            speaker = self._speakers_by_id.get(speaker_id)
            if speaker:
                speaker_names.append(speaker.name)
                speaker_urls.append(speaker.url)
            else:
                speaker_names.append("Unknown")
                speaker_urls.append("")

        return {
            "speaker_names": speaker_names,
            "speaker_urls": speaker_urls,
            "audiodharma_speaker_ids": primary_talk.speaker_ids,
            "audiodharma_talks": [talk.model_dump() for talk in talks],
            "audiodharma_urls": [f"https://www.audiodharma.org/talks/{talk.id}" for talk in talks],
        }

    def get_all_source_items(self) -> List[SourceItem]:
        """Returns a list of all unique YouTube videos found in the cache."""
        return [
            SourceItem(source_id=youtube_id, source_type=SourceType.YOUTUBE_VIDEO)
            for youtube_id in self._talks_by_youtube_id.keys()
        ]
