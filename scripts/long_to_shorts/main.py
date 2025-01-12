import os

from dotenv import load_dotenv

from services.pipelines.long_to_shorts.pipeline import LongToShortsPipeline

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("No Open API key provided.")


def main():
    pipeline = LongToShortsPipeline(openai_api_key)
    pipeline.run("https://www.youtube.com/watch?v=j53v0BFw5Io", "ru", """
    Analyze the podcast subtitiles and find the timestamps of 3 most interesting moments to create a YouTube shorts video.
    Output format example:
    00:00:00 - 00:00:50
    10:12:00 - 10:12:52
    15:00:00 - 15:00:10

    The output format are time intervals in the format HH:MM:SS - HH:MM:SS, with the start and end of the most interesting moments.
    Always follow the output format and reply only with the timestamps of the most interesting moments.
    """)


if __name__ == "__main__":
    main()
