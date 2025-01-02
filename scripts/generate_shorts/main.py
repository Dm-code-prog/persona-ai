import json
import os

from dotenv import load_dotenv

from scripts.generate_shorts.script_prompt import get_script_prompt
from services.shorts_pipeline.ass import generate_ass_with_highlights, group_characters_into_words
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

    # topic = input("Enter the video topic")
    # prompt = get_script_prompt(topic)

    # timings_dict = json.load(open('output/eleven_labs_ts_dict.json'))
    # generate_ass_with_highlights(timings_dict, 'output/subtitles.ass')

    # pipeline.run(prompt)

    pipeline.create_video(
        '/Users/kozlovdmitriy/dev/persona_ai_project/persona_ai/scripts/generate_shorts/output/elevenlabs_script.mp3',
        '/Users/kozlovdmitriy/dev/persona_ai_project/persona_ai/scripts/generate_shorts/output/subtitles.ass',
        [
            'output/pexels_footage_bodyweight exercises_0.mp4',
            'output/pexels_footage_bodyweight exercises_1.mp4',
            'output/pexels_footage_bodyweight exercises_2.mp4',
            'output/pexels_footage_bodyweight exercises_3.mp4',
            'output/pexels_footage_mental toughness_0.mp4',
            'output/pexels_footage_mental toughness_1.mp4',
            'output/pexels_footage_mental toughness_2.mp4',
            'output/pexels_footage_mental toughness_3.mp4',
            'output/pexels_footage_Navy SEAL training_0.mp4',
            'output/pexels_footage_Navy SEAL training_1.mp4',
            'output/pexels_footage_Navy SEAL training_2.mp4',
            'output/pexels_footage_Navy SEAL training_3.mp4',
        ]
    )


if __name__ == "__main__":
    main()
