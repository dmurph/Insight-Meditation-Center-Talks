# Improving Post-Processing, SEO, and Word Clouds

This document outlines planned improvements for the post-processing pipeline and the final presentation layer (HTML output) of the mirroring system.

## 1. Post-Processing and Data Enrichment

Once the primary markdown articles are generated, the system should support a pipeline of post-processing steps to further enrich the content.

*   **Keyword Analysis**:
    *   The existing `wordcloud.py` script, which performs TF-IDF analysis and generates keyword CSVs, should be integrated into the main orchestration flow. It should be triggered after a batch of new articles has been created.
    *   **Enhancement**: The primary goal is to take the results of this analysis and enrich the articles themselves. The orchestrator should:
        1.  Run the keyword analysis from `wordcloud.py`.
        2.  For each new article, read the corresponding keyword CSV file (e.g., `talks/cloud/YYYY-MM-DD - Title.csv`).
        3.  Extract the top N keywords (e.g., 20) based on the TF-IDF score.
        4.  Inject this list of keywords and their scores directly into the YAML frontmatter of the markdown article (e.g., under a `keywords` key). This makes the data immediately useful for the presentation layer and any future indexing systems.

## 2. Presentation Layer (HTML Generation)

The final output must be user-friendly, accessible, and performant. The issues with the current HTML generation should be addressed.

*   **Responsive Design**:
    *   **Data Grid**: The CSS for the talk list/grid needs to be updated to be fully responsive. Instead of fixed widths, use a modern CSS approach like Flexbox (`display: flex; flex-wrap: wrap;`) or CSS Grid with `auto-fit` and `minmax()` to allow the items to wrap gracefully on smaller screens.
    *   **Font Scaling**: Implement responsive typography. Use relative units like `rem` for font sizes and adjust the base font size using CSS media queries at different screen width breakpoints. This will ensure text is readable on all devices, which is crucial for user experience and SEO.
*   **SEO Improvements**:
    *   Ensure that the generated HTML has proper semantic structure (e.g., `<main>`, `<article>`, `<header>`).
    *   Dynamically generate meaningful `<title>` tags and `meta description` tags for each talk page based on its content. This is a significant factor for search engine ranking.
