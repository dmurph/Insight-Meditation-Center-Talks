import logging
import argparse
import os
import yt_dlp
from pathvalidate import sanitize_filename
import youtube
import audiodharma
import article_builder
import cache
from article import Article
import generate_html

logging.basicConfig(level=logging.INFO)


def process_youtube_videos(
    videos,
    limit=0,
    force_redownload_transcripts=False,
    force_ai_processing=False,
    do_not_stop_scan=False,
    stop_after_found_up_to_date_talks=10,
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

    logging.info(f"Loading transcriptions and creating articles")
    if not do_not_stop_scan:
        logging.info(
            f"Stopping after {stop_after_found_up_to_date_talks} up-to-date talks found."
        )
    for i, video in enumerate(videos):
        video_id = video["videoId"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            metadata = youtube.get_video_metadata(
                video_id,
                video_url,
                ydl,
                metadata_cache,
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
                            talk_urls.append(
                                f"https://www.audiodharma.org/talks/{talk_id}"
                            )
                            talk_headers_str += f"      `## {talk_title} ([link](https://www.audiodharma.org/talks/{talk_id}))`\n"

            if speaker_name == "Unknown":
                for speaker_id, speaker_info in speakers_data.items():
                    if speaker_info["name"].lower() in video_title.lower():
                        speaker_name = speaker_info["name"]
                        speaker_url = speaker_info["url"]
                        logging.info(
                            f"  -> Found speaker '{speaker_name}' in video title."
                        )
                        break

            if not force_ai_processing:
                article = Article.from_file(processed_output_path)
                if article:
                    logging.info(
                        f"Found existing talk article at {processed_output_path}"
                    )
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
                        logging.info(
                            f"  -> Metadata for is outdated. Updating:  {processed_output_path} "
                        )
                        article.save(processed_output_path)
                        continue

                    stop_after_found_up_to_date_talks -= 1
                    logging.info(
                        f"  -> Article is up-to-date. Skipping: {processed_output_path}"
                    )
                    if do_not_stop_scan:
                        continue
                    if stop_after_found_up_to_date_talks <= 0:
                        logging.info(
                            "  -> Stopping scan. Specify --do-not-stop-scan to not stop on up-to-date articles."
                        )
                        break
                    continue

            raw_transcript_path = youtube.get_transcript(
                video_id,
                video_title,
                upload_date,
                force_redownload_transcripts,
            )

            if raw_transcript_path:
                new_article = article_builder.create_article(
                    raw_transcript_path=raw_transcript_path,
                    video_title=video_title,
                    video_url=video_url,
                    speaker_name=speaker_name,
                    speaker_url=speaker_url,
                    talk_headers_str=talk_headers_str,
                    upload_date=upload_date,
                    talk_urls=talk_urls,
                    processed_output_path=processed_output_path,
                )

                if new_article:
                    new_article.save(processed_output_path)

        except Exception as e:
            logging.exception(f"  -> An unexpected error occurred in the main loop")
            break

    logging.info("\n--------------------\n")
    logging.info("Download process finished.")


def main():
    parser = argparse.ArgumentParser(
        description="Download and process YouTube channel transcripts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Scrape and generate command
    scrape_and_generate_parser = subparsers.add_parser(
        "scrape_and_generate",
        help="Scrape audiodharma.org and then process all YouTube videos found in the scrape.",
    )
    scrape_and_generate_parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit the number of videos to process (0 for no limit).",
    )
    scrape_and_generate_parser.add_argument(
        "--source",
        type=str,
        default="audiodharma",
        choices=["audiodharma", "imc-playlist"],
        help="The source of videos to process.",
    )
    scrape_and_generate_parser.add_argument(
        "--force-redownload-transcripts",
        action="store_true",
        help="Force redownload of raw transcripts even if they exist.",
    )
    scrape_and_generate_parser.add_argument(
        "--force-ai-processing",
        action="store_true",
        help="Force AI processing even if the processed file exists.",
    )
    scrape_and_generate_parser.add_argument(
        "--do-not-stop-scan",
        action="store_true",
        help="Don't stop processing the videos if a talk was already found as saved with the correct metadata, keep going for all videos in the playlist/channel/etc.",
    )

    # YouTube command
    youtube_parser = subparsers.add_parser(
        "youtube", help="Work with YouTube videos without scraping audiodharma."
    )
    youtube_sources = youtube_parser.add_subparsers(
        dest="fetch_source", help="Specify the type of source to fetch", required=True
    )

    video_id_source = youtube_sources.add_parser(
        "video-id", help="Use a video id by itself"
    )
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

    playlist_url_source = youtube_sources.add_parser(
        "playlist-id", help="Use a playlist id"
    )
    playlist_url_source.add_argument(
        "playlist_id",
        help="The id of a YouTube playlist. Defaults to all videos on the IMC channel.",
        type=str,
        default="UUGliqsod-tQoGiHahxS9Wig",
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
        "--save-after-pages",
        type=int,
        default=10,
        help="The number of pages processed between saving the files",
    )

    args = parser.parse_args()

    if args.command == "scrape_and_generate":
        videos = []
        audiodharma.run_scraper(
            start_page=1,
            max_pages=1000,
            talks_output_file="cache/audiodharma/talks.yaml",
            speakers_output_file="cache/audiodharma/speakers.yaml",
            save_after_pages=10,
        )
        if args.source == "audiodharma":
            audiodharma_talks, _ = cache.load_audiodharma_data()
            videos = [{"videoId": vid} for vid in audiodharma_talks.keys()]
        elif args.source == "imc-playlist":
            videos = youtube.get_video_urls(
                url_or_id="UUGliqsod-tQoGiHahxS9Wig",
                type=youtube.UrlType.PLAYLIST,
            )

        if not videos:
            logging.info("No videos found. Exiting.")
            return

        process_youtube_videos(
            videos,
            limit=args.limit,
            force_redownload_transcripts=args.force_redownload_transcripts,
            force_ai_processing=args.force_ai_processing,
            do_not_stop_scan=args.do_not_stop_scan,
        )
        generate_html.generate_all_html_pages()
    elif args.command == "youtube":

        if args.fetch_source == "video-id":
            videos = [{"videoId": args.id}]
        elif args.fetch_source == "channel-url":
            videos = youtube.get_video_urls(
                url_or_id=args.url,
                type=youtube.UrlType.CHANNEL,
            )
        elif args.fetch_source == "playlist-id":
            videos = youtube.get_video_urls(
                url_or_id=args.playlist_id,
                type=youtube.UrlType.PLAYLIST,
            )
        elif args.fetch_source == "audiodharma-cache":
            audiodharma_talks, _ = cache.load_audiodharma_data()
            videos = [{"videoId": vid} for vid in audiodharma_talks.keys()]
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
            do_not_stop_scan=args.do_not_stop_scan,
        )
    elif args.command == "audiodharma":
        audiodharma.run_scraper(
            start_page=args.start_page,
            max_pages=args.max_pages,
            talks_output_file="cache/audiodharma/talks.yaml",
            speakers_output_file="cache/audiodharma/speakers.yaml",
            save_after_pages=args.save_after_pages,
        )


if __name__ == "__main__":
    main()
