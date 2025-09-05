import os
import json
import logging
import yaml


def load_youtube_metadata_cache():
    metadata_cache_path = "cache/youtube/video_metadata_cache.json"
    if os.path.exists(metadata_cache_path):
        with open(metadata_cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_youtube_metadata_cache(cache_data):
    metadata_cache_path = "cache/youtube/video_metadata_cache.json"
    with open(metadata_cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=4)


def load_audiodharma_data():
    try:
        with open("cache/audiodharma/talks.yaml", "r", encoding="utf-8") as f:
            audiodharma_talks_data = yaml.safe_load(f)
        with open("cache/audiodharma/speakers.yaml", "r", encoding="utf-8") as f:
            speakers_data = yaml.safe_load(f)

        audiodharma_talks_map = {
            item["youtube_id"]: item["talks"] for item in audiodharma_talks_data
        }
        return audiodharma_talks_map, speakers_data
    except FileNotFoundError as e:
        logging.warning(f"Could not load audiodharma data: {e}. Continuing without it.")
        return {}, {}
