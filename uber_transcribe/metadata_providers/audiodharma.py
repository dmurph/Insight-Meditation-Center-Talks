import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict
import re
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup


from ..models import SourceItem, SourceType, AudioDharmaTalk, AudioDharmaSpeaker

logger = logging.getLogger(__name__)

class AudioDharmaScraper:
    """Scrapes talk and speaker data from audiodharma.org."""

    def parse_page(
        self, html_content: str
    ) -> Tuple[Dict[int, AudioDharmaTalk], Dict[int, AudioDharmaSpeaker]]:
        """Parses the HTML content of a single page of audiodharma.org talks."""
        talks: Dict[int, AudioDharmaTalk] = {}
        speakers: Dict[int, AudioDharmaSpeaker] = {}
        soup = BeautifulSoup(html_content, "html5lib")
        rows = soup.find_all("tr")

        if not rows or len(rows) <= 1:
            logger.warning("No data rows found in the table.")
            return talks, speakers

        for row in rows[1:]:
            title_tag = row.select_one(".playable-table-name a")
            speaker_tags = row.select(".playable-table-speaker a")
            date_tag = row.select_one(".playable-table-date")
            audio_tag = row.select_one("a.js-audio-select")

            if not title_tag or not speaker_tags or not date_tag:
                continue

            mp3_url = audio_tag.get("data-url") if audio_tag else None

            youtube_url = None
            desktop_video_anchor = row.select_one("a.video-modal-link")
            if desktop_video_anchor:
                youtube_url = desktop_video_anchor.get("data-embed-video-url")
            if not youtube_url:
                mobile_video_link = row.select_one('a.fa-video[href*="youtube.com"]')
                if mobile_video_link:
                    youtube_url = mobile_video_link.get("href")

            if not youtube_url:
                continue

            talk_url = "https://www.audiodharma.org" + title_tag["href"]
            try:
                talk_id = int(talk_url.split("/")[-1])
            except (ValueError, IndexError):
                logger.warning(f"Could not parse talk ID from URL: {talk_url}")
                continue

            parsed_youtube_url = urlparse(youtube_url)
            path_parts = [p for p in parsed_youtube_url.path.split("/") if p]
            youtube_id = path_parts[-1] if path_parts else None
            if not youtube_id:
                continue
                
            query_params = parse_qs(parsed_youtube_url.query)
            start_time_seconds = 0
            if "start" in query_params:
                start_time_seconds = int(re.sub(r"\D", "", query_params["start"][0]))
            elif "t" in query_params:
                start_time_seconds = int(re.sub(r"\D", "", query_params["t"][0]))


            for speaker_tag in speaker_tags:
                try:
                    speaker_url = "https://www.audiodharma.org" + speaker_tag["href"]
                    speaker_id = int(speaker_url.split("/")[-1])
                    speaker_name = speaker_tag.text.strip()

                    if speaker_id not in speakers:
                        speakers[speaker_id] = AudioDharmaSpeaker(
                            id=speaker_id, name=speaker_name
                        )
                    
                    talk = AudioDharmaTalk(
                        id=talk_id,
                        title=title_tag.text.strip(),
                        date=date_tag.text.strip().replace(".", "-"),
                        speaker_id=speaker_id,
                        start_time_seconds=start_time_seconds,
                        mp3_url=mp3_url,
                        youtube_id=youtube_id,
                    )
                    talks[talk_id] = talk

                except (ValueError, IndexError):
                    logger.warning(f"Could not parse speaker ID from URL: {speaker_url}")
                    continue
        
        return talks, speakers


class AudioDharmaProvider:
    """
    A MetadataProvider that enriches SourceItems with data scraped from audiodharma.org.
    """

    def __init__(self, cache_dir: Path = Path("cache/audiodharma")):
        """
        Initializes the provider and loads the audiodharma data from the cache.

        Args:
            cache_dir: The directory where the audiodharma JSON cache files are stored.
        """
        self.cache_dir = cache_dir
        self._talks_by_id: Dict[int, AudioDharmaTalk] = {}
        self._speakers_by_id: Dict[int, AudioDharmaSpeaker] = {}
        # Create an in-memory index to quickly find talks by youtube_id
        self._talks_by_youtube_id: Dict[str, List[AudioDharmaTalk]] = defaultdict(list)
        self._load_data_from_cache()

    def _load_data_from_cache(self):
        """Loads the talks and speakers data from the JSON cache files."""
        talks_path = self.cache_dir / "talks.json"
        speakers_path = self.cache_dir / "speakers.json"

        if not talks_path.exists() or not speakers_path.exists():
            logger.warning(
                f"AudioDharma cache files not found in {self.cache_dir}. "
                "Provider will not have any data."
            )
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

            logger.info(
                f"Successfully loaded AudioDharma cache with {len(self._talks_by_id)} talks "
                f"and {len(self._speakers_by_id)} speakers."
            )

        except Exception as e:
            logger.exception(f"Error loading AudioDharma cache: {e}")

    def bulk_load_data(self):
        """
        Ensures the data is loaded from the cache. In a future implementation,
        this method would trigger the live scraping logic if the cache is stale.
        For now, it does nothing as the constructor already loads the data.
        """
        logger.info(
            "AudioDharmaProvider: `bulk_load_data` called. "
            "Currently relying on existing cache."
        )
        if not self._talks_by_id or not self._speakers_by_id:
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
        talks = self._talks_by_youtube_id.get(video_id)
        if not talks:
            return None

        # Use the first talk to determine the primary speaker
        primary_talk = talks[0]
        speaker = self._speakers_by_id.get(primary_talk.speaker_id)

        speaker_name = "Unknown"
        speaker_url = ""
        if speaker:
            speaker_name = speaker.name
            speaker_url = speaker.url

        # Aggregate all talk URLs for this video
        talk_urls = [
            f"https://www.audiodharma.org/talks/{talk.id}"
            for talk in talks
        ]

        return {
            "speaker_name": speaker_name,
            "speaker_url": speaker_url,
            "audiodharma_speaker_id": primary_talk.speaker_id,
            "audiodharma_talks": [talk.model_dump() for talk in talks],
            "audiodharma_urls": talk_urls,
        }


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)

    # Create a dummy SourceItem for a known video
    test_video_id = "_FEo9XSSWdU"  # A known video ID from the cache
    item_to_test = SourceItem(
        source_id=test_video_id, source_type=SourceType.YOUTUBE_VIDEO
    )

    # Initialize the provider from the new cache location
    provider = AudioDharmaProvider(cache_dir=Path("uber_transcribe/cache/audiodharma"))

    # Perform the lookup
    metadata = provider.lookup(item_to_test)

    if metadata:
        logger.info(f"Successfully found metadata for video {test_video_id}:")
        import json

        logger.info(json.dumps(metadata, indent=2))
    else:
        logger.info(f"Could not find metadata for video {test_video_id}.")

