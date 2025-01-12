import json
import os

from dotenv import load_dotenv

from services.pipelines.subtitles import add_subtitles, group_words_into_sentences, group_chars_into_words
from services.pipelines.top5_generator.pipeline import TOP5Pipeline

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
    working_dir = input("Enter the working directory: ")

    subtitle_color = input(f"Enter the subtitle color, default is 'white': ")
    if not subtitle_color:
        subtitle_color = 'white'

    subtitle_bg_color = input(f"Enter the subtitle highlight color, default is '#7710e2 (purple)': ")
    if not subtitle_bg_color:
        subtitle_bg_color = '#7710e2'

    background_music_volume_adjustment = input(f"Enter the background music volume adjustment, default is -25 dB: ")
    if not background_music_volume_adjustment:
        background_music_volume_adjustment = -25
    # check that the volume adjustment is a number
    try:
        background_music_volume_adjustment = int(background_music_volume_adjustment)
    except ValueError:
        raise ValueError("Volume adjustment must be a number")

    pipeline = TOP5Pipeline(
        elevenlaps_api_key=elevenlabs_api_key,
        working_dir=working_dir,
    )

    footage_segments = {
        "intro": {
            "start": 1.0,
            "end": 2.0
        },
        "segments": [
            {
                "footage": "test/input/videos/overlay-1.mp4",
                "start": 2.0,
                "end": 8.0
            },
            {
                "footage": "test/input/videos/overlay-2.mp4",
                "start": 8.0,
                "end": 14.0
            },
            {
                "footage": "test/input/videos/overlay-3.mp4",
                "start": 14.0,
                "end": 22.0
            },
            {
                "footage": "test/input/videos/overlay-4.mp4",
                "start": 22.0,
                "end": 28.0
            },
            {
                "footage": "test/input/videos/overlay-5.mp4",
                "start": 28.0,
                "end": 34.0
            },
        ],
        "script_end": 60.0
    }

    pipeline.run(
        subtitle_color=subtitle_color,
        subtitle_highlight_color=subtitle_bg_color,
        background_music_volume_adjustment=background_music_volume_adjustment
    )


if __name__ == "__main__":
    main()
