import logging
import re
from typing import Dict, Tuple
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup

from .models import AudioDharmaTalk, AudioDharmaSpeaker


class AudioDharmaScraper:
    """Scrapes talk and speaker data from audiodharma.org HTML content."""

    def parse_page(
        self,
        html_content: str,
        speakers: Dict[int, AudioDharmaSpeaker] = None,
    ) -> Tuple[Dict[int, AudioDharmaTalk], Dict[int, AudioDharmaSpeaker]]:
        """Parses the HTML content of a single page of audiodharma.org talks."""
        if speakers is None:
            speakers = {}
        talks: Dict[int, AudioDharmaTalk] = {}
        soup = BeautifulSoup(html_content, "html5lib")
        rows = soup.find_all("tr")

        if not rows or len(rows) <= 1:
            logging.warning("No data rows found in the table.")
            return talks, speakers

        for row in rows[1:]:
            title_tag = row.select_one(".playable-table-name a")
            speaker_tags = row.select(".playable-table-speaker a")
            date_tag = row.select_one(".playable-table-date")
            audio_tag = row.select_one("a.js-audio-select")

            if not title_tag or not speaker_tags or not date_tag:
                continue

            speaker_ids = []
            for speaker_tag in speaker_tags:
                speaker_href = speaker_tag["href"]
                try:
                    speaker_id = int(speaker_href.split("/")[-1])
                except (ValueError, IndexError):
                    logging.warning(f"Could not parse speaker ID from {speaker_tag}")
                    continue
                
                speaker_name = speaker_tag.text.strip()
                logging.info(f"Found speaker: {speaker_name} ({speaker_id})")
                if speaker_id not in speakers:
                    speakers[speaker_id] = AudioDharmaSpeaker(
                        id=speaker_id, name=speaker_name
                    )
                speaker_ids.append(speaker_id)

            if not speaker_ids:
                logging.warning(f"No speakers found for talk: {title_tag.text}")
                continue

            mp3_url = audio_tag.get("data-url") if audio_tag else None

            youtube_url = None
            desktop_video_anchor = row.select_one("a.video-modal-link")
            if desktop_video_anchor:
                youtube_url = desktop_video_anchor.get("data-embed-video-url")
            if not youtube_url:
                mobile_video_link = row.select_one('a.fa-video[href*="youtube.com"]')
                youtube_url = mobile_video_link.get("href") if mobile_video_link else None

            talk_href = title_tag["href"]
            try:
                talk_id = int(talk_href.split("/")[-1])
            except (ValueError, IndexError):
                logging.warning(f"Could not parse talk ID from URL: {talk_href}")
                continue
            logging.info(f"Processing talk at {talk_href}");

            if not youtube_url:
                youtube_id = None
                start_time_seconds = 0
            else:
                parsed_youtube_url = urlparse(youtube_url)
                path_parts = [p for p in parsed_youtube_url.path.split("/") if p]
                youtube_id = path_parts[-1] if path_parts else None
                query_params = parse_qs(parsed_youtube_url.query)
                start_time_seconds = 0
                if "start" in query_params:
                    start_time_seconds = int(re.sub(r"\D", "", query_params["start"][0]))
                elif "t" in query_params:
                    start_time_seconds = int(re.sub(r"\D", "", query_params["t"][0]))
            
            talk = AudioDharmaTalk(
                id=talk_id,
                title=title_tag.text.strip(),
                date=date_tag.text.strip().replace(".", "-"),
                speaker_ids=speaker_ids,
                start_time_seconds=start_time_seconds,
                mp3_url=mp3_url,
                youtube_id=youtube_id,
            )
            logging.info(f"Processed talk {talk_id}: {title_tag.text}")
            talks[talk_id] = talk
        return talks, speakers
