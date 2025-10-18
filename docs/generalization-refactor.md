# Refactoring Plan: Generalizing the Mirroring System

This document outlines a plan to refactor the current IMC talk downloader into a more generalized, flexible, and robust system for mirroring content from various sources and enriching it with metadata from supplemental data sources.

## 1. Core Goals

*   **Decouple Sources & Metadata**: Separate the logic for fetching primary content from the logic for fetching supplemental metadata.
*   **Configurable & Pluggable**: Make it easy to add new sources and metadata providers via a configuration file without changing the core code.
*   **Robust & Reliable**: Improve matching, error handling, and the reliability of transcript downloading.
*   **Efficient**: Avoid redundant API calls and downloads.
*   **Portable**: Structure the project for eventual extraction into a standalone repository.

## 2. Interfaces and Data Models

We will use formal data structures (e.g., Python dataclasses) to ensure consistency.

*   **`SourceItem`**: The central object representing the primary content to be mirrored.
    *   **`source_id`**: A stable, unique ID (e.g., YouTube Video ID).
    *   **`source_type`**: An enum, e.g., `SourceType.YOUTUBE_VIDEO`.
    *   **`intrinsic_metadata`**: A dictionary for data inherent to the source (e.g., original YouTube title, upload date).
    *   **`supplemental_metadata`**: A dictionary to be populated by `MetadataProvider`s. To avoid key collisions, provider-specific IDs should be namespaced, e.g., `{ "audiodharma_speaker_id": 123, "another_provider_author_id": 456 }`.

*   **`MetadataProvider` (Interface)**: A pluggable module for fetching supplemental info. Each provider must implement:
    *   `__init__(self, config)`: Initializes the provider with its specific configuration.
    *   `lookup(self, source_item: SourceItem) -> dict`: Takes a `SourceItem` and returns a dictionary of metadata if a match is found. This is the core method for linking.
    *   `bulk_load_data(self)`: A method to scrape/load all its data into a local cache for faster lookups.

## 3. Configuration (`config.yaml`)

The entire process will be driven by a central configuration file.

```yaml
# The number of days to wait after a video is published before processing.
# This allows time for metadata to appear in external sources.
metadata_wait_days_delay: 2

# A list of methods for discovering SourceItems. The orchestrator will
# run all of these to compile a master list of items to process.
discovery_sources:
  - type: youtube_playlist
    playlist_id: "UUGliqsod-tQoGiHahxS9Wig" # IMC uploads playlist

  - type: audiodharma_scrape
    # This source finds YouTube IDs from the audiodharma site itself.
    # No extra config needed as it uses the cached data.

# A list of metadata providers to query for each SourceItem.
# They are queried in order; data from later providers can override earlier ones.
metadata_providers:
  - type: audiodharma
    # No specific config needed, uses the cache.

  - type: youtube_api
    # Future enhancement: use the YouTube API as another metadata source.
    api_key: "${YOUTUBE_API_KEY}" # Example of using env variables
```

## 4. The Orchestrator Staged Workflow

The main engine will execute a series of distinct stages, allowing for better modularity and intermediate artifacts.

*   **Stage 1: Update Metadata Caches**
    *   The orchestrator iterates through all configured `metadata_providers`.
    *   It calls the `provider.bulk_load_data()` method for each one.
    *   This ensures all local caches are up-to-date before any matching begins.

*   **Stage 2: Discover, Filter, and Match Source Items**
    *   Run all configured `discovery_sources` to compile a master list of `SourceItem` objects.
    *   Filter this list, removing any `SourceItem` that is newer than the `metadata_wait_days_delay`.
    *   For each remaining `SourceItem`, iterate through the `metadata_providers` and call `provider.lookup(source_item)` to enrich its `supplemental_metadata`.

*   **Stage 3: Generate AI-Cleaned Content**
    *   For each matched `SourceItem` from Stage 2 that doesn't have a final article:
        1.  Download the primary content (e.g., raw YouTube transcript).
        2.  Run the AI cleaning process.
        3.  Save the result as an intermediate artifact (e.g., in `cache/ai_cleaned_content/{source_id}.txt`). **This file contains only the processed body text, with no frontmatter.**

*   **Stage 4: Assemble Final Markdown Articles**
    *   For each AI-cleaned content file:
        1.  Load the corresponding enriched `SourceItem`.
        2.  Run any further post-processing on the cleaned text (e.g., keyword analysis via the `wordcloud` script to extract top N keywords).
        3.  Combine all metadata (intrinsic, supplemental, keywords) into a final frontmatter dictionary.
        4.  Prepend the frontmatter to the cleaned content.
        5.  Save the complete article to its final destination (e.g., `talks/{article_filename}.md`).

*   **Stage 5: Generate Presentation Layer**
    *   After the markdown generation is complete, run the `generate_html.py` script as a final, separate step to build the static site.

## 5. Project Structure Refactor

To support this, we could restructure the project:

```
.
├── orchestrator.py         # The main script to run the process
├── article_builder.py      # Handles creating the final markdown file
|
├── sources/                # Modules for primary content
│   ├── __init__.py
│   └── youtube.py          # Handles YouTube API interactions (metadata, transcripts)
|
└── metadata_providers/     # Modules for supplemental data
    ├── __init__.py
    └── audiodharma.py      # The existing scraper, refactored
```

## 6. Deeper Dive: Nuts & Bolts

*   **Decentralized Caching**: Each source and metadata provider is responsible for its own caching logic. This allows providers to choose the best caching strategy for their data (e.g., JSON, YAML, SQLite) and keeps the orchestrator clean. The provider's public interface will abstract away the caching details.
*   **Data Validation**: We can use `Pydantic` or `dataclasses` to define our models (`SourceItem`, etc.). This gives us type safety and automatic validation, preventing errors from malformed API/scrape data.
*   **Error Handling**: Each step (discovery, metadata lookup, download) should be wrapped in a `try...except` block. A failure for one `SourceItem` should be logged without crashing the entire process.
*   **Dependency Injection**: The `Orchestrator` will be initialized with instances of the discovery sources and metadata providers based on the config file. This makes the system modular and easy to test.

This more detailed plan should provide a strong and clear guide for the refactoring work.
