import yaml
import json
from pathlib import Path
from typing import Dict, Any, List
import logging


def migrate_talks_yaml_to_json(
    yaml_path: Path,
    json_path: Path,
):
    """
    Migrates the talks.yaml file to a talks.json file.

    The new format is a dictionary keyed by talk ID.
    """
    logging.basicConfig(level=logging.INFO)
    if not yaml_path.exists():
        logging.error(f"Error: {yaml_path} not found.")
        return

    with open(yaml_path, "r", encoding="utf-8") as f:
        try:
            talks_data: List[Dict[str, Any]] = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logging.error(f"Error reading YAML file: {e}")
            return

    if not talks_data:
        logging.warning("YAML file is empty or invalid.")
        return

    migrated_talks: Dict[int, Dict[str, Any]] = {}

    for item in talks_data:
        youtube_id = item.get("youtube_id")
        if not youtube_id:
            continue

        for talk in item.get("talks", []):
            talk_id = talk.get("id")
            if not talk_id:
                continue

            migrated_talks[talk_id] = {
                "title": talk.get("title"),
                "date": talk.get("date"),
                "speaker_id": talk.get("speaker_id"),
                "start_time_seconds": talk.get("startTimeSeconds"),
                "mp3_url": talk.get("mp3Url"),
                "youtube_id": youtube_id,
            }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(migrated_talks, f, indent=2, sort_keys=True)

    logging.info(f"Successfully migrated {len(migrated_talks)} talks to {json_path}")


if __name__ == "__main__":
    # Note: This script should be run from the root of the repository.
    cache_dir = Path("uber_transcribe/cache/audiodharma")
    talks_yaml_path = cache_dir / "talks.yaml"
    talks_json_path = cache_dir / "talks.json"

    migrate_talks_yaml_to_json(talks_yaml_path, talks_json_path)
