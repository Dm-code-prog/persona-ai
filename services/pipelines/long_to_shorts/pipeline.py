import os
import subprocess
import openai


class LongToShortsPipeline:
    openai_model = 'gpt-4o'
    openai_client = openai.OpenAI

    output_dir = "output"

    def __init__(self, openai_api_key: str):
        self.openai_client = openai.OpenAI(
            api_key=openai_api_key,
        )

        os.makedirs("output", exist_ok=True)

    def download_video_and_subtitles(self, youtube_url: str, lang: str) -> (str, str):
        """
        Downloads the YouTube video with auto-generated or normal subtitles
        using yt-dlp, and returns the path to the downloaded video and subtitle file.

        :param lang:
        :param youtube_url: The YouTube video URL.
        :return: The path to the downloaded video and subtitle file.
        """

        command = [
            "yt-dlp",
            youtube_url,
            "-o", os.path.join(self.output_dir, "long.%(ext)s"),
            "--merge-output-format", "mp4",
            "--write-auto-sub",
            "--sub-lang", lang,
            "--write-sub",
            "--sub-format", "srt",
            "--convert-subs", "srt",
        ]

        subprocess.run(command, check=True)

        return os.path.join(self.output_dir, "long.mp4"), os.path.join(self.output_dir, f"long.{lang}.srt")
