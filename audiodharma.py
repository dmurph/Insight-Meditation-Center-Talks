import requests
from bs4 import BeautifulSoup
import yaml
import argparse
from urllib.parse import urlparse, parse_qs
import re
import logging
import os
import time
import random
from enum import Enum

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class PageResult(Enum):
    END = 1
    NEW = 2
    KNOWN = 3


def scrape_page(page_num, existing_data, speakers_data) -> PageResult:
    """Scrapes a single page of audiodharma.org and returns a status: 'new', 'updated', or 'known'."""
    time.sleep(random.uniform(0.05, 1.0))
    url = f"https://www.audiodharma.org/talks?page={page_num}"
    logging.info(f"Scraping {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching page {page_num}: {e}")
        return PageResult.END

    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html5lib")
    rows = soup.find_all("tr")
    if not rows or len(rows) <= 1:
        logging.warning("No data rows found in the table.")
        return PageResult.END

    did_update = False
    did_append = False
    page_has_talks = False
    for row in rows[1:]:
        title_tag = row.select_one(".playable-table-name a")
        speaker_tag = row.select_one(".playable-table-speaker a")
        date_tag = row.select_one(".playable-table-date")
        audio_tag = row.select_one("a.js-audio-select")

        if not title_tag:
            continue
        page_has_talks = True

        mp3_url = None
        if audio_tag and "data-url" in audio_tag.attrs:
            mp3_url = audio_tag["data-url"]

        youtube_url = None
        desktop_video_anchor = row.select_one("a.video-modal-link")
        if desktop_video_anchor:
            youtube_url = desktop_video_anchor["data-embed-video-url"]

        # Try the mobile one if that wasn't found.
        if not youtube_url:
            mobile_video_link_tag = row.select_one('a.fa-video[href*="youtube.com"]')
            if mobile_video_link_tag:
                youtube_url = mobile_video_link_tag["href"]

        if not all([title_tag, speaker_tag, date_tag, youtube_url]):
            continue
        talk_title = title_tag.text.strip()
        talk_url = "https://www.audiodharma.org" + title_tag["href"]
        speaker_name = speaker_tag.text.strip()
        speaker_url = "https://www.audiodharma.org" + speaker_tag["href"]
        try:
            speaker_id = int(speaker_url.split("/")[-1])
        except (ValueError, IndexError):
            logging.warning(f"Could not parse speaker ID from URL: {speaker_url}")
            continue
        try:
            talk_id = int(talk_url.split("/")[-1])
        except (ValueError, IndexError):
            logging.warning(f"Could not parse talk ID from URL: {talk_url}")
            continue
        talk_date = date_tag.text.strip().replace(".", "-")

        if speaker_id not in speakers_data:
            speakers_data[speaker_id] = {"name": speaker_name, "url": speaker_url}

        parsed_url = urlparse(youtube_url)
        path_parts = [part for part in parsed_url.path.split("/") if part]
        video_id = path_parts[-1] if path_parts else None

        query_params = parse_qs(parsed_url.query)
        timestamp = 0
        if "start" in query_params:
            timestamp = int(re.sub(r"\D", "", query_params["start"][0]))
        elif "t" in query_params:
            timestamp = int(re.sub(r"\D", "", query_params["t"][0]))

        if not video_id:
            continue

        talk_entry = {
            "title": talk_title,
            "id": talk_id,
            "date": talk_date,
            "speaker_id": speaker_id,
            "start_time_seconds": timestamp,
            "mp3_url": mp3_url,
        }

        if video_id not in existing_data:
            existing_data[video_id] = {"youtube_id": video_id, "talks": []}

        existing_talks = existing_data[video_id]["talks"]
        talk_exists = False
        for i, existing_talk in enumerate(existing_talks):
            if ("id" in existing_talk and existing_talk["id"] == talk_id) or (
                "url" in existing_talk and existing_talk["url"] == talk_url
            ):
                talk_exists = True
                if existing_talk != talk_entry:
                    existing_talks[i] = talk_entry
                    logging.info(f"Updated talk: {talk_entry['title']}")
                    did_update = True
                break

        if not talk_exists:
            existing_talks.append(talk_entry)
            logging.info(f"Added talk: {talk_entry['title']}")
            did_append = True

    if not page_has_talks:
        return PageResult.END
    if did_update or did_append:
        return PageResult.NEW
    return PageResult.KNOWN


def save_talks_data(data, output_file):
    """Saves the scraped talks data to a YAML file, sorted by date."""
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Created output directory: {output_dir}")

    # Sort talks within each video by start time
    for video_id in data:
        data[video_id]["talks"].sort(key=lambda x: x["start_time_seconds"])

    # Sort the videos by the date of the first talk
    sorted_data = sorted(
        list(data.values()), key=lambda x: x["talks"][0]["date"], reverse=True
    )

    logging.info(f"Saving {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            sorted_data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            encoding="utf-8",
        )
    logging.info(f"Saved {output_file}")


def save_speakers_data(data, output_file):
    """Saves the speakers data to a YAML file, sorted by speaker ID."""
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    logging.info(f"Saving {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=True,
            allow_unicode=True,
            encoding="utf-8",
        )
    logging.info(f"Saved {output_file}")


def run_scraper(
    start_page=1,
    max_pages=1000,
    talks_output_file="cache/audiodharma/talks.yaml",
    speakers_output_file="cache/audiodharma/speakers.yaml",
    stop_after_known_pages=2,
    save_after_pages=10,
):
    """Main function to control scraping."""
    all_talks_data = {}
    speakers_data = {}

    pages_till_save = save_after_pages
    if os.path.exists(talks_output_file):
        logging.info(f"Loading existing talks data from {talks_output_file}...")
        with open(talks_output_file, "r", encoding="utf-8") as f:
            existing_yaml = yaml.safe_load(f)
            if existing_yaml:
                for entry in existing_yaml:
                    all_talks_data[entry["youtube_id"]] = entry
    if os.path.exists(speakers_output_file):
        logging.info(f"Loading existing speakers data from {speakers_output_file}...")
        with open(speakers_output_file, "r", encoding="utf-8") as f:
            loaded_speakers = yaml.safe_load(f)
            if loaded_speakers:
                speakers_data = {int(k): v for k, v in loaded_speakers.items()}

    assert stop_after_known_pages > 0
    logging.info(
        f"Scraping pages until the end or {stop_after_known_pages} pages of known talks are processed"
    )
    for i in range(start_page, start_page + max_pages):
        page_status = scrape_page(i, all_talks_data, speakers_data)
        if page_status == PageResult.END:
            logging.info("No more talks found.")
            break
        if page_status == PageResult.KNOWN:
            stop_after_known_pages -= 1
            if stop_after_known_pages <= 0:
                logging.info(
                    f"{stop_after_known_pages} pages of known data processed, stopping."
                )
                break
        pages_till_save -= 1
        if pages_till_save <= 0:
            pages_till_save = save_after_pages
            save_talks_data(all_talks_data, talks_output_file)
            save_speakers_data(speakers_data, speakers_output_file)

    # Do a final save.
    if pages_till_save != save_after_pages:
        save_talks_data(all_talks_data, talks_output_file)
        save_speakers_data(speakers_data, speakers_output_file)

    logging.info(f"Scraped {len(all_talks_data)} unique video entries.")
    logging.info(f"Final talks data saved to {talks_output_file}.")
    logging.info(f"Final speakers data saved to {speakers_output_file}.")
    logging.info("Done.")
