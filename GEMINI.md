This project downloads, processes, and stores video transcripts from YouTube, primarily from the Insight Meditation Center channel. It also scrapes and caches related talk metadata from `audiodharma.org`.

The project is structured as a series of focused modules orchestrated by the main `download.py` script.

### Core Modules

-   **`download.py`**: The main entry point and orchestrator. It handles command-line argument parsing for three main subcommands: `youtube`, `audiodharma`, and `scrape_and_generate`. It directs the workflow based on user input, calling on other modules to perform specific tasks.

-   **`youtube.py`**: Contains all functionality related to interacting with YouTube. This includes fetching lists of video URLs from channels or playlists (using `scrapetube`), downloading video metadata (using `yt-dlp`), and fetching raw transcript data (using `youtube_transcript_api`).

-   **`audiodharma.py`**: Handles all web scraping of the `audiodharma.org` website. It extracts talk metadata and speaker information and is responsible for creating and updating the local cache of this data.

-   **`ai.py`**: Responsible for the AI processing step. It takes a raw transcript and uses a prompt template to interact with the `gemini-cli` tool, returning the cleaned, formatted markdown content. It does not handle file I/O.

-   **`article.py`**: Defines the `Article` class, which represents a single talk. This class is responsible for managing the combination of metadata (title, speaker, etc.) and content. It handles the creation of frontmatter and provides methods to load an article from a file, update its metadata, and save it back to disk.

-   **`cache.py`**: Manages loading and saving of all cached data. This includes the YouTube video metadata cache and the `audiodharma.org` talks and speakers data, which are stored in YAML files.

-   **`filesystem.py`**: A utility module for filesystem-related operations, currently containing the `sanitize_filename` function to ensure file and directory names are valid across operating systems.

-   **`generate_html.py`**: A script to generate a browseable HTML interface for the downloaded talks. It creates an `index.html` with a sortable table of all talks, and individual pages for each speaker.

### Workflow Overview

1.  The user runs `download.py`. The primary command is `scrape_and_generate`, which automates the following steps.
2.  **Scraping**: The `audiodharma.py` module is called to scrape the website and update local caches.
3.  **YouTube Processing**:
    a. `youtube.py` fetches video URLs and metadata.
    b. The main loop in `download.py` iterates through each video, processing it, cleaning the transcript with `ai.py`, and saving it as an `Article` using `article.py`.
4.  **HTML Generation**: After processing, `generate_html.py` is called to create the `index.html` and speaker pages.
