import logging
import ai
from article import Article
import os

def create_article(
    raw_transcript_path: str,
    video_title: str,
    video_url: str,
    speaker_name: str,
    speaker_url: str,
    talk_headers_str: str,
    upload_date: str,
    talk_urls: list,
    processed_output_path: str,
) -> Article:
    """
    Processes a raw transcript, cleans it with AI, prepends a prefix,
    and returns an Article object.
    """
    cleaned_content = ai.clean_transcript(
        raw_transcript_path,
        video_title,
        video_url,
        speaker_name,
        speaker_url,
        talk_headers_str,
    )

    if not cleaned_content:
        return None

    try:
        with open("article_prefix.mdt", "r", encoding="utf-8") as f:
            prefix_template = f.read()
    except FileNotFoundError:
        logging.error("  -> Could not find article_prefix.mdt file!")
        return None

    prefix = prefix_template.replace("{video_title}", video_title)
    prefix = prefix.replace("{video_url}", video_url)
    prefix = prefix.replace("{speaker_name}", speaker_name)
    prefix = prefix.replace("{speaker_url}", speaker_url)

    full_content = f"{prefix}\n\n{cleaned_content}"

    new_article = Article(
        title=video_title,
        date=upload_date,
        video_url=video_url,
        speaker_name=speaker_name,
        speaker_url=speaker_url,
        talk_urls=talk_urls,
        content=full_content,
        filepath=processed_output_path,
    )
    return new_article
