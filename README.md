# Insight Meditation Center Talks

The purpose of this repo is to download and mirror the transcriptions of talks from Insigne Meditation Center in Redwood City. Currently this is all from their [youtube channel](https://www.youtube.com/@InsightMeditationCenter).


## Talk Storage Structure

The 'live' directory is the live talks, and 'video' are the other videos.

## Script usage

This script downloads video transcripts from a YouTube channel, processes them with an AI for cleanup, and saves them locally.

### Basic Usage

```bash
GEMINI_API_KEY=your_api_key python download.py <channel_url> <output_dir>
```

-   `<channel_url>`: The full URL of the YouTube channel or sub-channel-page.
-   `<output_dir>`: The local directory where files will be saved.

### Options

-   `--limit <number>`: Limit the number of videos to process. Default is 0 (no limit).
-   `--redownload-video-urls`: Force a re-download of the channel's video list, overwriting the local `videos.json` cache.
-   `--force-redownload-transcripts`: Force re-downloading of the raw transcript files, even if they algiready exist locally.
-   `--force-ai-processing`: Force the AI processing step to run, even if the final processed file already exists.
-   `--raw-extension <ext>`: Specify the file extension for raw transcripts. Default is `rawtranscript`.
-   `--processed-extension <ext>`: Specify the file extension for AI-processed transcripts. Default is `md`.

### Example

```bash
# Download all transcripts of the live videos from the channel and save them to the 'live' directory (note that this is only the 'live' videos)
python download.py "https://www.youtube.com/@InsightMeditationCenter/streams" "streams"

# Note: Using 'https://www.youtube.com/@InsightMeditationCenter' are the non-live videos, which is different.

# Download the 5 most recent live transcripts, forcing AI processing
python download.py "https://www.youtube.com/@InsightMeditationCenter/streams" "streams" --limit 5 --force-ai-processing
```

