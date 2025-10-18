import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def consolidate_metadata():
    """
    Scans all JSON files in the old youtube cache, extracts metadata for each
    video, and consolidates it into a single master metadata file.
    """
    youtube_cache_dir = Path("cache/youtube")
    output_path = Path("uber_transcribe/cache/youtube/master_metadata.json")
    
    if not youtube_cache_dir.exists():
        logging.error(f"YouTube cache directory not found at {youtube_cache_dir}. Aborting.")
        return

    master_metadata = {}
    
    logging.info(f"Scanning for JSON files in {youtube_cache_dir}...")
    json_files = list(youtube_cache_dir.glob("*.json"))
    logging.info(f"Found {len(json_files)} files to process.")

    for json_file in json_files:
        logging.info(f"Processing {json_file.name}...")
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                
                # Handle dict format (e.g., video_metadata_cache.json)
                if isinstance(data, dict):
                    for video_id, metadata in data.items():
                        if video_id not in master_metadata:
                            master_metadata[video_id] = {}
                        # Update, prioritizing existing values but filling missing ones
                        master_metadata[video_id].update(metadata)

                # Handle list format (e.g., playlist caches)
                elif isinstance(data, list):
                    for video in data:
                        video_id = video.get("videoId")
                        if not video_id:
                            continue
                        
                        if video_id not in master_metadata:
                            master_metadata[video_id] = {}
                        
                        # Extract title if it doesn't exist or is generic
                        if not master_metadata[video_id].get("title") or master_metadata[video_id].get("title") == "Unknown Title":
                            title_runs = video.get("title", {}).get("runs")
                            if title_runs:
                                title = title_runs[0].get("text")
                                if title:
                                    master_metadata[video_id]["title"] = title
            
            except json.JSONDecodeError:
                logging.warning(f"Could not parse {json_file.name}, skipping.")

    # Final check for missing titles
    for video_id, metadata in master_metadata.items():
        if "title" not in metadata:
            metadata["title"] = "Unknown Title"
        if "upload_date" not in metadata:
            metadata["upload_date"] = "0000-00-00" # Placeholder date

    logging.info(f"Consolidated metadata for {len(master_metadata)} unique videos.")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(master_metadata, f, indent=2)
        
    logging.info(f"Successfully saved master metadata to {output_path}")

if __name__ == "__main__":
    consolidate_metadata()
