import os
import glob
from collections import defaultdict
from article import Article
import argparse
import urllib.parse
import cache

def get_all_talks(directory="talks"):
    talks = []
    for filepath in glob.glob(os.path.join(directory, "*.md")):
        article = Article.from_file(filepath)
        if article:
            talks.append(article)
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
        rows_html += f"""
        <tr>
            <td>{talk.date}</td>
            <td><a href="{talk_url}">{talk.title}</a></td>
            <td>{talk.speaker_name}</td>
            <td>{links}</td>
        </tr>"""
    return rows_html

def generate_speaker_table_rows(speaker_talks, speakers_data):
    rows_html = ""
    sorted_speaker_ids = sorted(speaker_talks.keys(), key=lambda x: speakers_data.get(x, {}).get('name', 'Unknown'))

    for speaker_id in sorted_speaker_ids:
        talks = speaker_talks[speaker_id]
        speaker_name = speakers_data.get(speaker_id, {}).get('name', 'Unknown Speaker')
        talk_count = len(talks)
        rows_html += f"""
        <tr>
            <td><a href="./speaker/{speaker_id}.html">{speaker_name}</a></td>
            <td>{talk_count}</td>
        </tr>"""
    return rows_html

def generate_speaker_html(speaker_id, talks, speakers_data, output_dir="talks/speaker"):
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{speaker_id}.html")
    
    speaker_name = speakers_data.get(speaker_id, {}).get('name', 'Unknown Speaker')
    table_rows = generate_talk_table_rows(talks, relative_path_prefix="../")

    with open(filepath, "w") as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Talks by {speaker_name}</title>
    <script src="../talk-table.js"></script>
</head>
<body>
    <h1>Talks by {speaker_name}</h1>
    <talk-table>
        <table>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </talk-table>
</body>
</html>""")

def generate_index_html(all_talks, speaker_talks, speakers_data, output_path="talks/index.html"):
    talk_table_rows = generate_talk_table_rows(all_talks, relative_path_prefix="./")
    speaker_table_rows = generate_speaker_table_rows(speaker_talks, speakers_data)

    with open(output_path, "w") as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>All Talks</title>
    <script src="talk-table.js"></script>
</head>
<body>
    <h1>Speakers</h1>
    <speaker-table>
        <table>
            <tbody>
                {speaker_table_rows}
            </tbody>
        </table>
    </speaker-table>

    <h1>All Talks</h1>
    <talk-table>
        <table>
            <tbody>
                {talk_table_rows}
            </tbody>
        </table>
    </talk-table>
</body>
</html>""")

def generate_all_html_pages():
    parser = argparse.ArgumentParser(description="Generate HTML files for talks.")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="talks",
        help="The directory to output the HTML files to.",
    )
    args, _ = parser.parse_known_args()

    _, speakers_data = cache.load_audiodharma_data()
    all_talks = get_all_talks()
    speaker_talks = group_talks_by_speaker(all_talks)

    speaker_dir = os.path.join(args.output_dir, "speaker")
    for speaker_id, talks in speaker_talks.items():
        generate_speaker_html(speaker_id, talks, speakers_data, output_dir=speaker_dir)

    index_path = os.path.join(args.output_dir, "index.html")
    generate_index_html(all_talks, speaker_talks, speakers_data, output_path=index_path)

if __name__ == "__main__":
    generate_all_html_pages()
