import re


def sanitize_filename(title):
    """
    Removes characters that are illegal in file names across different OS.
    """
    # Change / to - for some ok structure.
    sanitized = re.sub(r"[\\/]", "-", title)
    # Remove illegal characters
    sanitized = re.sub(r'[\\/*?:"<<>>|"]', "", sanitized)
    # Replace sequences of whitespace with a single space
    sanitized = re.sub(r"\\s+", " ", sanitized)
    # Trim leading/trailing whitespace
    return sanitized.strip()
