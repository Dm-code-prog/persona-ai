import os
import time

from dotenv import load_dotenv

from scripts.generate_shorts.script_2nd_shot_prompt import get_2shot_script_prompt
from scripts.generate_shorts.script_prompt import get_script_prompt
from services.pipelines.general.old_pipeline import ShortVideoPipeline

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

    topic = input("Enter the video topic:\n")

    start = time.time()

    script = pipeline.generate_script(
        get_script_prompt(topic)
    )
    script_2nd_shot = pipeline.generate_script_2nd_shot(
        get_2shot_script_prompt(script)
    )

    speech_file, words, sentences = pipeline.text_to_speech(script_2nd_shot)

    script_with_footages = pipeline.generate_script_with_footages(script_2nd_shot)

    footages = pipeline.get_footages(script=script_with_footages, words=words)

    pipeline.edit_video(
        speech_file,
        footages,
        sentences,
    )

    end = time.time()
    print(f"⌛ Generated a video in {end - start} seconds")


if __name__ == "__main__":
    main()
