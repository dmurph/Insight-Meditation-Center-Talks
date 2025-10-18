import json
import logging
import os
from pathlib import Path
from pathvalidate import sanitize_filename

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def migrate_transcripts():
    """
    Renames old transcript files (named with date and title) to new files
    (named with video_id) in the new cache location.
    """
    old_transcript_dir = Path("cache/raw_transcripts")
    new_transcript_dir = Path("uber_transcribe/cache/youtube/raw_transcripts")
    metadata_cache_path = Path("uber_transcribe/cache/youtube/video_metadata_cache.json")

    if not metadata_cache_path.exists():
        logging.error(f"Metadata cache not found at {metadata_cache_path}. Cannot migrate.")
        return

    with open(metadata_cache_path, "r", encoding="utf-8") as f:
        metadata_cache = json.load(f)

    # Create a reverse lookup map from filename to video_id
    filename_to_id_map = {}
    for video_id, metadata in metadata_cache.items():
        # Recreate the old filename format
        safe_filename = sanitize_filename(f"{metadata['upload_date']} - {metadata['title']}")
        filename_to_id_map[safe_filename] = video_id

    if not old_transcript_dir.exists():
        logging.warning(f"Old transcript directory not found at {old_transcript_dir}. Nothing to migrate.")
        return

    logging.info(f"Scanning {old_transcript_dir} for transcripts to migrate...")
    migrated_count = 0
    skipped_count = 0
    for old_file in old_transcript_dir.iterdir():
        if old_file.suffix in ['.srt', '.json']:
            base_name = old_file.stem
            if base_name in filename_to_id_map:
                video_id = filename_to_id_map[base_name]
                new_filename = f"{video_id}{old_file.suffix}"
                new_filepath = new_transcript_dir / new_filename
                
                # Copy the file to the new location with the new name
                with open(old_file, 'rb') as f_in, open(new_filepath, 'wb') as f_out:
                    f_out.write(f_in.read())
                
                logging.info(f"Migrated: {old_file.name} -> {new_filename}")
                migrated_count += 1
            else:
                logging.warning(f"Could not find a video_id match for {old_file.name}. Skipping.")
                skipped_count += 1
    
    logging.info("\n--- Migration Complete ---")
    logging.info(f"Successfully migrated {migrated_count} transcript files.")
    logging.info(f"Skipped {skipped_count} files (no match found in metadata cache).")

if __name__ == "__main__":
    migrate_transcripts()
