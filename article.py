import frontmatter
import os
import logging
import yaml


class Article:
    def __init__(
        self,
        title,
        date,
        video_url,
        speaker_name,
        speaker_url,
        talk_urls,
        content,
        filepath,
    ):
        self.title = title
        self.date = date
        self.video_url = video_url
        self.speaker_name = speaker_name
        self.speaker_url = speaker_url
        self.talk_urls = talk_urls
        self.content = content
        self.filepath = filepath

    def to_markdown(self):
        """Combines metadata and content into a markdown string with frontmatter."""
        post = frontmatter.Post(self.content)
        post["title"] = self.title
        post["date"] = self.date
        post["video_url"] = self.video_url
        post["speaker"] = self.speaker_name
        post["speaker_url"] = self.speaker_url
        post["talk_urls"] = self.talk_urls
        return frontmatter.dumps(post, Dumper=yaml.SafeDumper, default_style='"')

    def save(self, file_path):
        """Saves the article to a file."""
        try:
            output_dir = os.path.dirname(file_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.to_markdown())
            logging.info(f"  -> Successfully saved article to: {file_path}")
            return True
        except Exception as e:
            logging.error(f"  -> Error saving article to {file_path}: {e}")
            return False

    def update_metadata(
        self, title, date, video_url, speaker_name, speaker_url, talk_urls
    ):
        """Updates the article's metadata attributes."""
        self.title = title
        self.date = date
        self.video_url = video_url
        self.speaker_name = speaker_name
        self.speaker_url = speaker_url
        self.talk_urls = talk_urls

    @classmethod
    def from_file(cls, file_path):
        """Loads an article from a markdown file."""
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

                article = cls(
                    title=post.get("title"),
                    date=post.get("date"),
                    video_url=post.get("video_url"),
                    speaker_name=post.get("speaker"),
                    speaker_url=post.get("speaker_url"),
                    talk_urls=post.get("talk_urls"),
                    content=post.content,
                    filepath=file_path,
                )
                return article
        except Exception as e:
            logging.warning(
                f"  -> Could not parse existing file {file_path}. Will re-process. Error: {e}"
            )
            return None
