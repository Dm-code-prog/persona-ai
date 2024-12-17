import os

from dotenv import load_dotenv

from scripts.generate_shorts.prompt import prompt
from services.shorts_pipeline.pipeline import ShortVideoPipeline

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
pexels_api_key = os.getenv("PEXELS_API_KEY")

# Check if API keys are provided
if not openai_api_key:
    raise ValueError("No Open API key provided.")
if not elevenlabs_api_key:
    raise ValueError("No 11labs API key provided.")
if not pexels_api_key:
    raise ValueError("No Pexels API key provided.")


def main():
    pipeline = ShortVideoPipeline(
        open_api_key=openai_api_key,
        elevenlaps_api_key=elevenlabs_api_key,
        pexels_api_key=pexels_api_key,
    )

    # pipeline.run(prompt)

    footage_paths = pipeline.get_footage_for_tags(['morning workout', 'quick exercise', 'energized person', 'health'])

    pipeline.create_video(
        speech_path='output/elevenlabs_script.mp3',
        subs_path='output/subtitles.srt',
        footage_paths=footage_paths
    )


if __name__ == "__main__":
    main()
