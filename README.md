# Insight Meditation Center Talks

This project downloads video transcripts from YouTube and scrapes talk metadata from `audiodharma.org`. It processes the raw transcripts using a Generative AI to produce cleaned, formatted, and enriched markdown files suitable for a personal knowledge base.

## Installation

Set up a Python virtual environment and install the required dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You must also have the `gemini-cli` tool installed and configured in your system's PATH.

## Script Usage

The script is organized into two main subcommands: `youtube` for downloading and processing video transcripts, and `audiodharma` for scraping website data.

### 1. Scraping AudioDharma.org

Before processing YouTube videos, it's recommended to update the local cache of talk and speaker metadata from `audiodharma.org`. This data is used to enrich the final markdown files with speaker names and talk URLs.

```bash
python download.py audiodharma
```

This command scrapes the website and saves the data to `cache/audiodharma/talks.yaml` and `cache/audiodharma/speakers.yaml`. It will efficiently stop once it encounters a page with no new information.

-   `--full-scrape`: Use this flag to force the scraper to check every single page, regardless of whether new data is found.

### 2. Processing YouTube Transcripts

The `youtube` command fetches video transcripts, cleans them with an AI, and saves them as markdown files.

#### **Commands**

-   **`channel-url`**: Process videos from a channel URL.
    ```bash
    python download.py youtube channel-url <url> [options]
    ```
-   **`playlist-id`**: Process videos from a playlist ID.
    ```bash
    python download.py youtube playlist-id <id> [options]
    ```
-   **`video-id`**: Process a single video by its ID.
    ```bash
    python download.py youtube video-id <id> [options]
    ```

#### **Common Options**

-   `--limit <number>`: Limit the number of videos to process. Default is 0 (no limit).
-   `--force-ai-processing`: Force the AI processing step, even if the final markdown file already exists.
-   `--force-redownload-transcripts`: Force re-downloading of raw transcripts, even if they are already cached.
-   `--do-not-stop-scan`: By default, the script stops when it finds an up-to-date, existing article. Use this flag to continue processing all videos in the list.
-   `--rebuild-video-url-cache`: Force a complete re-download of the video list from a channel or playlist.
-   `--skip-video-url-download`: Use the cached video list instead of fetching a new one.
-   `--skip-metadata-cache`: Fetch fresh video metadata from YouTube instead of using the cache.

### Examples

```bash
# 1. Update the audiodharma.org data cache first.
python download.py audiodharma

# 2. Process all new videos from the IMC live stream channel.
# The script will stop once it finds a video that has already been processed and is up-to-date.
python download.py youtube channel-url "https://www.youtube.com/@InsightMeditationCenter/streams"

# Process the 5 most recent videos from the main videos tab, forcing AI processing.
python download.py youtube channel-url "https://www.youtube.com/@InsightMeditationCenter/videos" --limit 5 --force-ai-processing

# Process a single video.
python download.py youtube video-id "dQw4w9WgXcQ"
```

## Project Structure

-   `download.py`: The main script orchestrating all operations.
-   `youtube.py`, `audiodharma.py`, `ai.py`, `article.py`, `cache.py`, `filesystem.py`: Modules containing the core logic for interacting with services, processing data, and managing files.
-   `cache/`: Contains all cached data, including scraped website info and YouTube metadata.
-   `raw_transcripts/`: Stores the raw, unprocessed transcript files.
-   `talks/`: Stores the final, AI-cleaned and formatted markdown files.