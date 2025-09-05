import logging
import os
import subprocess
from typing import Optional

def clean_transcript(
    raw_transcript_path: str,
    youtube_title: str,
    youtube_url: str,
    speaker_name: str,
    speaker_url: str,
    talk_headers: str,
) -> Optional[str]:
    """
    Processes a raw transcript file using gemini-cli to produce clean markdown content.
    Returns the content as a string, or None if an error occurs.
    """
    PROMPT_TEMPLATE = "prompt_template.mdt"

    logging.info(f"  -> Processing with AI: {raw_transcript_path}")
    if not os.path.exists(raw_transcript_path):
        logging.warning(
            "  -> Cannot perform AI processing because raw transcript is missing."
        )
        return None

    transcript_extension = raw_transcript_path.split(".")[-1]

    try:
        with open(PROMPT_TEMPLATE, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logging.error("  -> Could not find prompt template file!")
        return None

    try:
        with open(raw_transcript_path, "r", encoding="utf-8") as f:
            raw_transcript_data = f.read()

        prompt = prompt_template
        prompt = prompt.replace("{video_title}", youtube_title)
        prompt = prompt.replace("{video_url}", youtube_url)
        prompt = prompt.replace("{speaker_name}", speaker_name)
        prompt = prompt.replace("{speaker_url}", speaker_url)
        prompt = prompt.replace("{talk_headers}", talk_headers)
        prompt = prompt.replace("{transcript_extension}", transcript_extension)
        prompt = prompt.replace("{raw_transcript_data}", raw_transcript_data)

        process = subprocess.run(
            ["gemini"],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )

        clean_transcript = process.stdout.strip()

        # Remove markdown block fences
        lines = clean_transcript.split('\n')
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        
        return '\n'.join(lines)

    except FileNotFoundError:
        logging.error("  -> AI Processing Error: 'gemini-cli' command not found.")
        logging.error(
            "     Please ensure the Gemini CLI is installed and in your system's PATH."
        )
        return None
    except subprocess.CalledProcessError as e:
        logging.error("  -> AI Processing Error: The 'gemini-cli' command failed.")
        logging.error(f"     Return Code: {e.returncode}")
        logging.error(f"     Stderr: {e.stderr}")
        return None
    except Exception as e:
        logging.error(f"  -> An unexpected error occurred during AI processing: {e}")
        return None
