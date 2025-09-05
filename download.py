import logging
import argparse
import os
import yt_dlp
from filesystem import sanitize_filename
import youtube
import audiodharma
import ai
import cache
from article import Article

logging.basicConfig(level=logging.INFO)


def process_youtube_videos(
    videos,
    limit=0,
    force_redownload_transcripts=False,
    force_ai_processing=False,
    skip_metadata_cache=False,
    do_not_stop_scan=False,
):
    if not videos:
        return

    if limit > 0:
        logging.info(f"Limiting to the first {limit} videos.")
        videos = videos[:limit]

    audiodharma_talks_map, speakers_data = cache.load_audiodharma_data()

    ydl_opts = {"quiet": True, "no_warnings": True}
    ydl = yt_dlp.YoutubeDL(ydl_opts)

    metadata_cache = cache.load_youtube_metadata_cache()

    for i, video in enumerate(videos):
        video_id = video["videoId"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            metadata = youtube.get_video_metadata(
                video_id, video_url, ydl, metadata_cache, skip_metadata_cache
            )
            video_title = metadata["title"]
            upload_date = metadata["upload_date"]

            cache.save_youtube_metadata_cache(metadata_cache)

            logging.info(f"\n[{i+1}/{len(videos)}] Processing: {video_title}")

            safe_filename = sanitize_filename(f"{upload_date} - {video_title}")
            processed_output_path = os.path.join("talks", f"{safe_filename}.md")

            speaker_name = "Unknown"
            speaker_url = ""
            talk_urls = []
            talk_headers_str = ""

            if video_id in audiodharma_talks_map:
                talks = audiodharma_talks_map[video_id]
                if talks:
                    speaker_id = talks[0].get("speaker_id")
                    if speaker_id and speaker_id in speakers_data:
                        speaker_info = speakers_data[speaker_id]
                        speaker_name = speaker_info.get("name", "Unknown")
                        speaker_url = speaker_info.get("url", "")
                    
                    for talk in talks:
                        talk_id = talk.get("id")
                        talk_title = talk.get("title")
                        if talk_id and talk_title:
                            talk_urls.append(f"https://www.audiodharma.org/talks/{talk_id}")
                            talk_headers_str += f"      `## {talk_title} ([link](https://www.audiodharma.org/talks/{talk_id}))`\n"

            if not force_ai_processing:
                article = Article.from_file(processed_output_path)
                if article:
                    original_markdown = article.to_markdown()
                    article.update_metadata(
                        title=video_title,
                        date=upload_date,
                        video_url=video_url,
                        speaker_name=speaker_name,
                        speaker_url=speaker_url,
                        talk_urls=talk_urls,
                    )
                    if article.to_markdown() != original_markdown:
                        logging.info(f"  -> Metadata for {processed_output_path} is outdated. Updating.")
                        article.save(processed_output_path)
                        continue
                    else:
                        logging.info(f"  -> Article {processed_output_path} is up-to-date. Skipping.")
                    if not do_not_stop_scan:
                        logging.info("  -> Stopping scan. Specify --do-not-stop-scan to not stop on up-to-date articles.")
                        break
                    continue

            raw_transcript_path = youtube.get_transcript(
                video_id,
                video_title,
                upload_date,
                force_redownload_transcripts,
            )

            if raw_transcript_path:
                cleaned_content = ai.clean_transcript(
                    raw_transcript_path,
                    video_title,
                    video_url,
                    speaker_name,
                    speaker_url,
                    talk_headers_str,
                )

                if cleaned_content:
                    new_article = Article(
                        title=video_title,
                        date=upload_date,
                        video_url=video_url,
                        speaker_name=speaker_name,
                        speaker_url=speaker_url,
                        talk_urls=talk_urls,
                        content=cleaned_content,
                    )
                    new_article.save(processed_output_path)

        except Exception as e:
            logging.error(f"  -> An unexpected error occurred in the main loop: {e}")

    logging.info("\n--------------------")
    logging.info("Download process finished.")


def main():
    parser = argparse.ArgumentParser(
        description="Download and process YouTube channel transcripts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # YouTube command
    youtube_parser = subparsers.add_parser("youtube", help="Work with YouTube videos.")
    youtube_sources = youtube_parser.add_subparsers(
        dest="fetch_source", help="Specify the type of source to fetch", required=True
    )

    video_id_source = youtube_sources.add_parser("video-id", help="Use a video id by itself")
    video_id_source.add_argument(
        "id", help="The ID of a single YouTube video to process.", type=str
    )

    channel_url_source = youtube_sources.add_parser(
        "channel-url", help="Use a channel url"
    )
    channel_url_source.add_argument(
        "url",
        help="The URL of the YouTube channel. Defaults to the IMC live stream channel",
        type=str,
        default="https://www.youtube.com/@InsightMeditationCenter/streams",
    )
    channel_url_source.add_argument(
        "--rebuild-video-url-cache",
        action="store_true",
        help="Force a complete redownload of all video URLs, rebuilding the cache.",
    )
    channel_url_source.add_argument(
        "--skip-video-url-download",
        action="store_true",
        help="Skip downloading video URLs and use the existing cache.",
    )

    playlist_url_source = youtube_sources.add_parser(
        "playlist-id", help="Use a playlist id"
    )
    playlist_url_source.add_argument(
        "playlist_id",
        help="The id of a YouTube playlist. Defaults to all videos on the IMC channel.",
        type=str,
        default="UUGliqsod-tQoGiHahxS9Wig",
    )
    playlist_url_source.add_argument(
        "--rebuild-video-url-cache",
        action="store_true",
        help="Force a complete redownload of all video URLs, rebuilding the cache.",
    )
    playlist_url_source.add_argument(
        "--skip-video-url-download",
        action="store_true",
        help="Skip downloading video URLs and use the existing cache.",
    )

    youtube_parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit the number of videos to process (0 for no limit).",
    )
    youtube_parser.add_argument(
        "--force-redownload-transcripts",
        action="store_true",
        help="Force redownload of raw transcripts even if they exist.",
    )
    youtube_parser.add_argument(
        "--force-ai-processing",
        action="store_true",
        help="Force AI processing even if the processed file exists.",
    )
    youtube_parser.add_argument(
        "--skip-metadata-cache",
        action="store_true",
        help="Skip using the metadata cache and force re-fetching from YouTube.",
    )
    youtube_parser.add_argument(
        "--do-not-stop-scan",
        action="store_true",
        help="Don't stop processing the videos if a talk was already found as saved with the correct metadata, keep going for all videos in the playlist/channel/etc.",
    )

    # Audiodharma command
    audiodharma_parser = subparsers.add_parser(
        "audiodharma", help="Scrape talks from audiodharma.org."
    )
    audiodharma_parser.add_argument(
        "--start_page", type=int, default=1, help="The starting page number to scrape."
    )
    audiodharma_parser.add_argument(
        "--max_pages",
        type=int,
        default=1000,
        help="Maximum number of pages to scrape.",
    )
    audiodharma_parser.add_argument(
        "--talks_output_file",
        type=str,
        default="cache/audiodharma/talks.yaml",
        help="Output YAML file for talks.",
    )
    audiodharma_parser.add_argument(
        "--speakers_output_file",
        type=str,
        default="cache/audiodharma/speakers.yaml",
        help="Output YAML file for speakers.",
    )
    audiodharma_parser.add_argument(
        "--overwrite-existing-file",
        action="store_true",
        help="Overwrite the existing YAML file instead of updating it.",
    )
    audiodharma_parser.add_argument(
        "--full-scrape",
        action="store_true",
        default=False,
        help="Perform a full scrape up to max_pages, ignoring existing data.",
    )
    audiodharma_parser.add_argument(
        "--save-after-pages",
        type=int,
        default=10,
        help="The number of pages processed between saving the files",
    )

    args = parser.parse_args()

    if args.command == "youtube":
        rebuild_cache = getattr(args, "rebuild_video_url_cache", False)
        skip_download = getattr(args, "skip_video_url_download", False)

        if args.fetch_source == "video-id":
            videos = [{"videoId": args.id}]
        elif args.fetch_source == "channel-url":
            videos = youtube.get_video_urls(
                url_or_id=args.url,
                type=youtube.UrlType.CHANNEL,
                rebuild_cache=rebuild_cache,
                skip_download=skip_download,
            )
        elif args.fetch_source == "playlist-id":
            videos = youtube.get_video_urls(
                url_or_id=args.playlist_id,
                type=youtube.UrlType.PLAYLIST,
                rebuild_cache=rebuild_cache,
                skip_download=skip_download,
            )
        else:
            parser.print_help()
            return

        if not videos:
            logging.info("No videos found. Exiting.")
            return

        process_youtube_videos(
            videos,
            limit=args.limit,
            force_redownload_transcripts=args.force_redownload_transcripts,
            force_ai_processing=args.force_ai_processing,
            skip_metadata_cache=args.skip_metadata_cache,
            do_not_stop_scan=args.do_not_stop_scan,
        )
    elif args.command == "audiodharma":
        audiodharma.run_scraper(
            start_page=args.start_page,
            max_pages=args.max_pages,
            talks_output_file=args.talks_output_file,
            speakers_output_file=args.speakers_output_file,
            overwrite_existing_file=args.overwrite_existing_file,
            full_scrape=args.full_scrape,
            save_after_pages=args.save_after_pages,
        )


if __name__ == "__main__":
    main()