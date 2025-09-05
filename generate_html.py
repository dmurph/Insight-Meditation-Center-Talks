import os
import glob
from collections import defaultdict
from article import Article
import argparse
import urllib.parse
from datetime import datetime
import logging

def get_all_talks(directory="talks"):
    talks = []
    for filepath in glob.glob(os.path.join(directory, "*.md")):
        article = Article.from_file(filepath)
        if article:
            if article.date:
                talks.append(article)
            else:
                logging.warning(f"Article at {filepath} has no date, skipping.")

    # Sort talks by date, newest first
    talks.sort(key=lambda x: datetime.strptime(x.date, '%Y-%m-%d'), reverse=True)
    return talks

def group_talks_by_speaker(talks):
    speaker_talks = defaultdict(list)
    for talk in talks:
        speaker_id = "unknown"
        if talk.speaker_url:
            speaker_id = talk.speaker_url.split("/")[-1]
        speaker_talks[speaker_id].append(talk)
    return speaker_talks

def generate_talk_table_rows(talks, relative_path_prefix=""):
    rows_html = ""
    for talk in talks:
        filename = os.path.basename(talk.filepath)
        html_filename = os.path.splitext(filename)[0] + ".html"
        encoded_filename = urllib.parse.quote(html_filename)
        talk_url = f"{relative_path_prefix}{encoded_filename}"

        links = f'<a href="{talk.video_url}">YouTube</a>'
        if talk.talk_urls:
            for url in talk.talk_urls:
                links += f' <a href="{url}">AudioDharma</a>'
        
        speaker_id = "unknown"
        if talk.speaker_url:
            speaker_id = talk.speaker_url.split("/")[-1]
        
        speaker_html = talk.speaker_name
        if speaker_id != "unknown":
            speaker_html = f'<a href="{relative_path_prefix}speaker/{speaker_id}.html">{talk.speaker_name}</a>'

        rows_html += f"""
        <tr>
            <td>{talk.date}</td>
            <td><a href="{talk_url}">{talk.title}</a></td>
            <td>{speaker_html}</td>
            <td>{links}</td>
        </tr>"""
    return rows_html

def generate_speaker_table_rows(speaker_talks):
    rows_html = ""
    # Sort by speaker name
    sorted_speaker_ids = sorted(speaker_talks.keys(), key=lambda speaker_id: (speaker_talks[speaker_id][0].speaker_name or 'Unknown').lower())

    for speaker_id in sorted_speaker_ids:
        talks = speaker_talks[speaker_id]
        speaker_name = talks[0].speaker_name or "Unknown Speaker"
        speaker_url = talks[0].speaker_url

        audiodharma_link = ""
        if speaker_url:
            audiodharma_link = f'<td><a href="{speaker_url}">link</a></td>'
        else:
            audiodharma_link = '<td>N/A (unknown)</td>'

        rows_html += f"""
        <tr>
            <td><a href="./speaker/{speaker_id}.html">{speaker_name}</a></td>
            {audiodharma_link}
        </tr>"""
    return rows_html

def generate_speaker_html(speaker_id, talks, output_dir="talks/speaker"):
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{speaker_id}.html")
    
    speaker_name = talks[0].speaker_name if talks else "Unknown"
    speaker_url = talks[0].speaker_url if talks else None
    table_rows = generate_talk_table_rows(talks, relative_path_prefix="../")

    audiodharma_link_html = ""
    if speaker_url:
        audiodharma_link_html = f'<a href="{speaker_url}">audiodharma speaker page</a>'

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Talks by {speaker_name}</title>
    <script src="../talk-table.js"></script>
    <link rel="stylesheet" href="../style.css">
    <meta charset="UTF-8">
</head>
<body class="speaker-page">
    <div class="container">
        <div class="talk-list">
            <h2><a href="../index.html">Insight Meditation Center Talks</a> by {speaker_name}</h2>
            <p>
                This is an index of all ai-generated talk publications 
                <a href="https://github.com/dmurph/Insight-Meditation-Center-Talks">processed here</a>
                so far by this speaker, using transcripts from the Insight Meditation Center
                <a href="https://www.youtube.com/@InsightMeditationCenter">YouTube channel</a>,
                with supplemental information scraped from <a href="https://www.audiodharma.org/">AudioDharma</a>.
                See their {audiodharma_link_html} for more talks and information.
            </p>
            <talk-table>
                <table>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </talk-table>
        </div>
    </div>
</body>
</html>""")

def generate_index_html(all_talks, speaker_talks, output_path="talks/index.html"):
    talk_table_rows = generate_talk_table_rows(all_talks, relative_path_prefix="./")
    speaker_table_rows = generate_speaker_table_rows(speaker_talks)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(
            f"""<!DOCTYPE html>
<html>
<head>
    <title>Insight Meditation Center Talks</title>
    <script src="talk-table.js"></script>
    <link rel="stylesheet" href="style.css">
    <meta charset="UTF-8">
</head>
<body class="index-page">
    <h1>Insight Meditation Center Talks</h1>
    <p>
        This is an index of all ai-generated talk publications 
        <a href="https://github.com/dmurph/Insight-Meditation-Center-Talks">processed here</a>
        so far, using transcripts from the Insight Meditation Center
        <a href="https://www.youtube.com/@InsightMeditationCenter">YouTube channel</a>,
        with supplemental information scraped from <a href="https://www.audiodharma.org/">AudioDharma</a>.
    </p>
    <div class="container">
        <div class="speaker-list">
            <h2>Speakers</h2>
            <speaker-table>
                <table>
                    <tbody>
                        {speaker_table_rows}
                    </tbody>
                </table>
            </speaker-table>
        </div>
        <div class="talk-list">
            <h2>All Processed Talks</h2>
            <talk-table>
                <table>
                    <tbody>
                        {talk_table_rows}
                    </tbody>
                </table>
            </talk-table>
        </div>
    </div>
</body>
</html>"""
        )

def generate_all_html_pages():
    parser = argparse.ArgumentParser(description="Generate HTML files for talks.")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="talks",
        help="The directory to output the HTML files to.",
    )
    args, _ = parser.parse_known_args()

    all_talks = get_all_talks()
    speaker_talks = group_talks_by_speaker(all_talks)

    speaker_dir = os.path.join(args.output_dir, "speaker")
    for speaker_id, talks in speaker_talks.items():
        generate_speaker_html(speaker_id, talks, output_dir=speaker_dir)

    index_path = os.path.join(args.output_dir, "index.html")
    generate_index_html(all_talks, speaker_talks, output_path=index_path)

if __name__ == "__main__":
    generate_all_html_pages()
