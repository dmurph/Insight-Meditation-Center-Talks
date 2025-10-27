import yaml
import json
from pathlib import Path
from typing import Dict, Any
import logging

def migrate_speakers_yaml_to_json(
    yaml_path: Path,
    json_path: Path,
):
    """
    Migrates the speakers.yaml file to a speakers.json file.

    The new format is a dictionary keyed by speaker ID.
    """
    logging.basicConfig(level=logging.INFO)
    if not yaml_path.exists():
        logging.error(f"Error: {yaml_path} not found.")
        return

    with open(yaml_path, "r", encoding="utf-8") as f:
        try:
            speakers_data: Dict[int, Dict[str, Any]] = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logging.error(f"Error reading YAML file: {e}")
            return

    if not speakers_data:
        logging.warning("YAML file is empty or invalid.")
        return

    # The YAML is already in the desired format (id -> dict), so we just need to add the id to the object
    # and ensure it's keyed correctly.
    migrated_speakers: Dict[int, Dict[str, Any]] = {}
    for speaker_id, speaker_info in speakers_data.items():
        migrated_speakers[speaker_id] = {
            "name": speaker_info.get("name"),
        }


    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(migrated_speakers, f, indent=2, sort_keys=True)

    logging.info(f"Successfully migrated {len(migrated_speakers)} speakers to {json_path}")


if __name__ == "__main__":
    # Note: This script should be run from the root of the repository.
    cache_dir = Path("uber_transcribe/cache/audiodharma")
    speakers_yaml_path = cache_dir / "speakers.yaml"
    speakers_json_path = cache_dir / "speakers.json"

    migrate_speakers_yaml_to_json(speakers_yaml_path, speakers_json_path)
