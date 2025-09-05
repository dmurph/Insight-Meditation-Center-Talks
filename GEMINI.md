This project downloads, processes, and stores video transcripts from YouTube, primarily from the Insight Meditation Center channel. It also scrapes and caches related talk metadata from `audiodharma.org`.

The project is structured as a series of focused modules orchestrated by the main `download.py` script.

### Core Modules

-   **`download.py`**: The main entry point and orchestrator. It handles command-line argument parsing for two main subcommands: `youtube` and `audiodharma`. It directs the workflow based on user input, calling on other modules to perform specific tasks.

-   **`youtube.py`**: Contains all functionality related to interacting with YouTube. This includes fetching lists of video URLs from channels or playlists (using `scrapetube`), downloading video metadata (using `yt-dlp`), and fetching raw transcript data (using `youtube_transcript_api`).

-   **`audiodharma.py`**: Handles all web scraping of the `audiodharma.org` website. It extracts talk metadata and speaker information and is responsible for creating and updating the local cache of this data.

-   **`ai.py`**: Responsible for the AI processing step. It takes a raw transcript and uses a prompt template to interact with the `gemini-cli` tool, returning the cleaned, formatted markdown content. It does not handle file I/O.

-   **`article.py`**: Defines the `Article` class, which represents a single talk. This class is responsible for managing the combination of metadata (title, speaker, etc.) and content. It handles the creation of frontmatter and provides methods to load an article from a file, update its metadata, and save it back to disk.

-   **`cache.py`**: Manages loading and saving of all cached data. This includes the YouTube video metadata cache and the `audiodharma.org` talks and speakers data, which are stored in YAML files.

-   **`filesystem.py`**: A utility module for filesystem-related operations, currently containing the `sanitize_filename` function to ensure file and directory names are valid across operating systems.

### Workflow Overview

1.  The user runs `download.py` with either the `youtube` or `audiodharma` subcommand.
2.  **For `audiodharma`**: The `audiodharma.py` module is called to scrape the website and update the local YAML caches (`cache/audiodharma/`).
3.  **For `youtube`**:
    a.  The `youtube.py` module fetches the list of video URLs and their metadata, managing the YouTube-specific caches.
    b.  The main loop in `download.py` iterates through each video.
    c.  It checks if a processed article file already exists in the `talks/` directory. The `article.py` module is used to load the existing file and check if its metadata is outdated. If it is, the file is updated in place, and the script moves to the next video (unless `--do-not-stop-scan` is specified).
    d.  If the article does not exist, `youtube.py` is called to download the raw transcript.
    e.  The raw transcript is passed to `ai.py`, which returns the cleaned markdown content.
    f.  An `Article` object is created with the metadata and cleaned content.
    g.  The `article.py` module's `save()` method is called to write the final `.md` file with frontmatter to the `talks/` directory.