# Uber Transcribe System

This directory contains a modular, configurable pipeline for discovering, fetching, enriching, and processing content from various online sources.

## Design Goals

The goal of this system is to replace the collection of top-level scripts with a robust, testable, and extensible pipeline. It separates concerns, allowing new sources (e.g., other YouTube channels, podcasts) and new metadata providers to be added with minimal changes to the core logic.

## Architecture

The system is composed of several key components that are coordinated by the `Orchestrator`.

1.  **Orchestrator (`orchestrator.py`)**
    *   The central coordinator of the entire pipeline.
    *   It reads a `config.yaml` file to determine which sources and providers to activate.
    *   It executes the workflow in distinct stages (e.g., updating caches, discovering items, processing).

2.  **SourceItem (`models.py`)**
    *   The central data model that represents a single piece of content (e.g., a YouTube video).
    *   It is passed between the different components of the system. It holds both intrinsic metadata (from the source) and supplemental metadata (from providers).

3.  **Discovery Sources (`sources/`)**
    *   These modules are responsible for finding an initial list of `SourceItem` objects.
    *   **Example:** `sources.youtube.YouTubeSource` discovers all videos in a given YouTube playlist.

4.  **Metadata Providers (`metadata_providers/`)**
    *   These modules are responsible for enriching `SourceItem` objects with additional information.
    *   They can also act as a discovery source themselves by exposing a `get_all_source_items()` method.
    *   **Example:** `metadata_providers.audiodharma.AudioDharmaProvider` takes a `SourceItem` representing a YouTube video and adds metadata scraped from `audiodharma.org`, such as the speaker's name and the corresponding talk URLs.

## Workflow

The `Orchestrator` runs the pipeline in a series of stages:

1.  **Stage 1: Update Metadata Caches**
    *   The orchestrator calls `update_cache()` on all configured metadata providers.
    *   Each provider is responsible for fetching the latest data from its source (e.g., scraping a website) and updating its local cache files.

2.  **Stage 2: Discover & Match**
    *   The orchestrator calls `discover_items()` on all configured discovery sources to get an initial list of all possible `SourceItem`s.
    *   It then iterates through this list and passes each item to the `lookup()` method of all configured metadata providers, which add supplemental data.

3.  **(Future) Stage 3: Process Items**
    *   The final, enriched list of `SourceItem` objects will be passed to subsequent stages for processing, which will include:
        *   Downloading transcripts.
        *   Performing AI-based cleaning and formatting.
        *   Generating the final article files.

## Configuration (`config.yaml`)

The entire pipeline is configured via `uber_transcribe/config.yaml`. This file defines which sources and providers are active.

```yaml
# Example config.yaml
discovery_sources:
  - type: youtube_playlist
    playlist_id: "UUGliqsod-tQoGiHahxS9Wig" # IMC uploads playlist

metadata_providers:
  - type: audiodharma
```

## Usage

The system is run by instantiating and executing the `Orchestrator`.

```python
# Example usage
from pathlib import Path
from uber_transcribe.orchestrator import Orchestrator

config_file = Path("uber_transcribe/config.yaml")
orchestrator = Orchestrator(config_path=config_file)

orchestrator.run_stage_1_update_metadata_caches()
enriched_items = orchestrator.run_stage_2_discover_and_match()

# ... further processing ...
```
