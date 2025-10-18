import json
import logging
from pathlib import Path
from pathvalidate import sanitize_filename
import re
from thefuzz import fuzz

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def find_best_match(title_to_match: str, all_titles: list, threshold: int = 2) -> str | None:
    """
    Finds the best fuzzy match for a title from a list of candidates.

    Args:
        title_to_match: The title from the old filename.
        all_titles: A list of all possible titles from the master metadata.
        threshold: The maximum Levenshtein distance to consider a match.

    Returns:
        The best matching title, or None if no single best match is found.
    """
    best_match = None
    best_ratio = -1
    
    for candidate_title in all_titles:
        # fuzz.ratio gives a similarity score from 0 to 100
        ratio = fuzz.ratio(title_to_match, candidate_title)
        
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate_title
        elif ratio == best_ratio:
            # Ambiguous match
            best_match = None

    # Convert threshold to a ratio. A distance of 2 on a ~100 char string is roughly a ratio of 98.
    # Let's use a slightly more generous ratio to be safe.
    if best_match and best_ratio >= 95:
        return best_match
    
    return None


def migrate_transcripts():
    """
    Renames old transcript files using fuzzy title matching.
    """
    old_transcript_dir = Path("cache/raw_transcripts")
    new_transcript_dir = Path("uber_transcribe/cache/youtube/raw_transcripts")
    master_metadata_path = Path("uber_transcribe/cache/youtube/master_metadata.json")

    if not master_metadata_path.exists():
        logging.error(f"Master metadata file not found at {master_metadata_path}. Run consolidate_metadata.py first.")
        return

    logging.info(f"Loading master metadata from {master_metadata_path}...")
    with open(master_metadata_path, "r", encoding="utf-8") as f:
        master_metadata = json.load(f)

    # Create a map from sanitized title to video_id
    title_to_id_map = {}
    for video_id, metadata in master_metadata.items():
        if metadata.get("title"):
            sanitized_title = sanitize_filename(metadata["title"])
            title_to_id_map[sanitized_title] = video_id
    
    all_sanitized_titles = list(title_to_id_map.keys())
    logging.info(f"Built lookup map with {len(all_sanitized_titles)} titles.")

    if not old_transcript_dir.exists():
        logging.warning(f"Old transcript directory not found at {old_transcript_dir}. Nothing to migrate.")
        return

    logging.info(f"Scanning {old_transcript_dir} for transcripts to migrate...")
    migrated_count = 0
    skipped_count = 0
    
    title_extractor_regex = re.compile(r"^\d{4}-\d{2}-\d{2} - (.*)$")

    for old_file in old_transcript_dir.iterdir():
        if old_file.suffix not in ['.srt', '.json']:
            continue

        base_name = old_file.stem
        match = title_extractor_regex.match(base_name)
        
        video_id = None
        if match:
            title_part = match.group(1)
            sanitized_title_part = sanitize_filename(title_part)
            
            best_match_title = find_best_match(sanitized_title_part, all_sanitized_titles, threshold=2)
            
            if best_match_title:
                video_id = title_to_id_map[best_match_title]
        
        elif base_name in master_metadata:
            video_id = base_name

        if video_id:
            new_filename = f"{video_id}{old_file.suffix}"
            new_filepath = new_transcript_dir / new_filename
            
            with open(old_file, 'rb') as f_in, open(new_filepath, 'wb') as f_out:
                f_out.write(f_in.read())
            
            logging.info(f"Migrated: {old_file.name} -> {new_filename}")
            migrated_count += 1
        else:
            logging.warning(f"Could not find a confident match for {old_file.name}. Skipping.")
            skipped_count += 1
    
    logging.info("\n--- Migration Complete ---")
    logging.info(f"Successfully migrated/copied {migrated_count} transcript files.")
    logging.info(f"Skipped {skipped_count} files (no confident match found).")

if __name__ == "__main__":
    migrate_transcripts()
