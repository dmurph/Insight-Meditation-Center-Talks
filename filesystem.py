import subprocess
import os
from datetime import datetime
import logging

def get_git_last_modified_for_files(file_paths):
    """
    Gets the last modified date for a list of files from git.
    Returns a dictionary mapping file path to its last commit date in ISO 8601 format.
    """
    last_modified_map = {}
    for file_path in file_paths:
        if not os.path.exists(file_path):
            continue
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%cI", "--", file_path],
                capture_output=True,
                text=True,
                check=True,
            )
            iso_date = result.stdout.strip()
            if iso_date:
                # Return only the date part
                last_modified_map[file_path] = datetime.fromisoformat(
                    iso_date
                ).isoformat()
        except (subprocess.CalledProcessError, FileNotFoundError):
            logging.exception("Could not get git timestamp.")
            # Fallback to file system mtime if git fails or file is not committed
            lastmod_timestamp = os.path.getmtime(file_path)
            last_modified_map[file_path] = datetime.fromtimestamp(
                lastmod_timestamp
            ).isoformat()
    return last_modified_map