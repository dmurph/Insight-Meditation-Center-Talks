This project is designed to download and process video transcripts from the Insight Meditation Center's YouTube channel.

The primary script, `download.py`, handles the entire workflow:
1.  **Fetches Video List:** It can take either a `channel-url` or a `video-id`. If a channel is provided, it uses the `scrapetube` library to get a list of all videos from a specified YouTube channel URL. This list is cached in a `videos/<channel_name>.json` file to avoid redundant downloads. The filename is derived from the channel URL. Only the `videoId` for each video is stored.
2.  **Downloads Transcripts:** For each video, it first checks for a local `.srt` file with a matching name in the `raw_transcripts` directory. If found, it uses that file as the transcript. Otherwise, it uses the `youtube_transcript_api` to download the raw transcript data. These are saved as `.rawtranscript` files in the `raw_transcripts` directory.
3.  **Processes with AI:** The raw transcript is then passed to a Generative AI model via the `gemini-cli` command-line tool. A detailed prompt instructs the AI to clean up the transcript, format it into readable markdown, correct potential transcription errors common with specialized vocabulary (like Pali terms in Dharma talks), and add a disclaimer.
4.  **Saves Final Output:** The cleaned, AI-processed content is saved as a markdown (`.md`) file in the `talks` directory.

The script is highly configurable through command-line arguments, allowing users to:
*   Process a single video with `video-id`.
*   Process all videos from a channel with `channel-url`.
*   Limit the number of videos to process (`--limit`).
*   Force re-downloading of the video list or transcripts (`--redownload-video-urls`, `--force-redownload-transcripts`).
*   Force the AI processing step even if an output file already exists (`--force-ai-processing`).

The `README.md` provides clear instructions on how to install dependencies and run the script with various options, including examples for downloading different types of content from the channel (e.g., live streams vs. regular video uploads).

Key libraries used:
*   `scrapetube`: For fetching video lists from YouTube channels.
*   `yt-dlp`: For extracting video metadata like title and upload date.
*   `youtube_transcript_api`: For downloading video transcripts.
*   `argparse`: For parsing command-line arguments.
*   `subprocess`: To run the external `gemini-cli` tool for AI processing.

To run the project, the user needs to have Python installed, along with the packages listed in `requirements.txt`, and must have the `gemini-cli` tool installed and configured in their system's PATH. Using venv is highly recommended, and `pip install -r requirements.txt` can be used to install all required dependencies.