This file contains context for AI agents working in this repository.

@README.md

## AI Agent Instructions

-   The primary workflow for this project is the `scrape_and_generate` command in `download.py`. When asked to update the talks, this is the command that should be used.
-   The `audiodharma.org` website is the primary source of truth for talk metadata. The YouTube channel is the source for transcripts. The goal is to link these two sources.
-   The project is designed to be run automatically by a GitHub Action. When making changes, be mindful that the script needs to run in a headless environment.
-   The `gemini-cli` tool is used for the AI processing step. The prompt templates are in the root directory (`prompt_template.mdt` and `prompt_template_no_talks.mdt`).
-   When modifying the core logic, ensure that the caching mechanisms are respected to avoid unnecessary processing and API calls. The script is designed to be efficient and stop when it finds up-to-date content.
-   The final output of the project is the `talks/` directory, which contains the generated markdown files and the HTML interface. The `generate_html.py` script is responsible for creating the HTML files.