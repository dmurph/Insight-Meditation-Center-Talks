# Insight Meditation Center Talks

The purpose of this repo is to download and mirror the transcriptions of talks from Insigne Meditation Center in Redwood City. Currently this is all from their [youtube channel](https://www.youtube.com/@InsightMeditationCenter).


## File Storage Structure

The script organizes files as follows:

-   `videos/<videos_fetch_source>.json`: A cache of video information. The filename is derived from the channel URL.
-   `videos/video_metadata.json`: A cache of video metadata (title, upload date, URL) to avoid re-fetching from YouTube.
-   `raw_transcripts/`: Stores the raw, unprocessed transcript files downloaded from YouTube. This includes both `.srt` files you may have locally and `.rawtranscript` files downloaded by the script.
-   `talks/`: Stores the final, AI-cleaned and formatted markdown files.

## Script usage

This script downloads video transcripts from a YouTube channel, processes them with an AI for cleanup, and saves them locally.

### Basic Usage

Start the python enviroment:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Commands

The script now uses sub-commands to specify the source of the videos.

#### `channel-url`

Download all videos from a channel URL.

```bash
GEMINI_API_KEY=your_api_key python download.py channel-url <url> [options]
```

-   `<url>`: The full URL of the YouTube channel (e.g., `https://www.youtube.com/@InsightMeditationCenter/streams`).

#### `video-id`

Download a single video by its ID.

```bash
GEMINI_API_KEY=your_api_key python download.py video-id <id> [options]
```

-   `<id>`: The YouTube video ID.

### Global Options

These options can be used with either `channel-url` or `video-id`.

-   `--limit <number>`: Limit the number of videos to process. Default is 0 (no limit).
-   `--redownload-video-urls`: (Only for `channel-url`) Force a re-download of the channel's video list, overwriting the local cache.
-   `--force-redownload-transcripts`: Force re-downloading of the raw transcript files, even if they already exist locally.
-   `--force-ai-processing`: Force the AI processing step to run, even if the final processed file already exists.
-   `--skip-metadata-cache`: Skip using the metadata cache and force re-fetching from YouTube.

### Examples

```bash
# Download all transcripts and do ai processing for all of the live videos from the channel
python download.py channel-url "https://www.youtube.com/@InsightMeditationCenter/streams"

# Download the 5 most recent non-live videos, forcing AI processing to overwrite any already saved talks.
python download.py channel-url "https://www.youtube.com/@InsightMeditationCenter/videos" --limit 5 --force-ai-processing

# Download a single video
python download.py video-id "dQw4w9WgXcQ"
```