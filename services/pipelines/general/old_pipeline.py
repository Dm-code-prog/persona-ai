import base64
import json
import os
import subprocess
import time
import uuid
import warnings
from typing import Dict, List

import elevenlabs
import openai
from elevenlabs import VoiceSettings

from elevenlabs.client import ElevenLabs

from openai import OpenAI

import services.pipelines.ffmpeg as ffmpeg
import services.pipelines.subtitles as subs
from services.pipelines.general.footage_parser import parse_and_time_script


class ShortVideoPipeline:
    pipeline_id: uuid.UUID = None

    openai_model = 'gpt-4o'
    openai_client = openai.OpenAI

    elevenlabs_client: elevenlabs.ElevenLabs = None

    media_dir = './media'
    # The directory where all the output files are stored, equals to ./output/{pipeline_id}
    output_dir = None

    def __init__(self, open_api_key: str, elevenlaps_api_key: str, pexels_api_key: str):
        self.pexels_api_key = pexels_api_key
        self.openai_client = OpenAI(
            api_key=open_api_key,
        )
        self.elevenlabs_client = ElevenLabs(api_key=elevenlaps_api_key)

        self.pipeline_id = uuid.uuid4()
        self.output_dir = f'./output/{self.pipeline_id}'

        os.makedirs(self.output_dir)

    def edit_video(
            self,
            speech_path: str,
            timed_footages: List[Dict],
            # List of {"type": "video" or "photo", "filename": str, "start": float, "end": float}
            sentences: list
    ) -> str:
        """
        Creates a final video from timed footages so that:
          1. The total timeline from 0..audio_duration is fully covered (no gaps).
          2. Each footage is clipped to its (end-start) length if it's a video,
             or 1 second if it's a photo.
          3. Subtitles and audio are added for the entire audio duration.
        """

        speech_path = os.path.abspath(speech_path)
        concat_timeline_path = os.path.join(self.output_dir, 'concatenated_timeline.mp4')
        concat_with_subs = os.path.join(self.output_dir, 'concat_with_subs.mp4')
        concat_with_speech = os.path.join(self.output_dir, 'concat_with_speech.mp4')
        output_path = os.path.join(self.output_dir, 'output.mp4')

        music_path = os.path.join(self.media_dir, 'uplifting_1.mp3')  # for background music (tmp)

        edit_start = time.time()

        # 1) Check audio duration
        h264_encoder = ffmpeg.get_gpu_accelerated_h264_encoder()
        if h264_encoder is None:
            h264_encoder = 'libx264'

        audio_duration = ffmpeg.get_media_duration(speech_path)
        if audio_duration <= 0:
            raise ValueError("The audio duration is 0 or invalid.")

        # 2) Sort footages by start time and verify no gaps
        sorted_footages = sorted(timed_footages, key=lambda f: f["start"])

        # Check that the first starts at 0
        first_start = sorted_footages[0]["start"]
        if abs(first_start - 0.0) > 1e-6:
            raise ValueError(f"First footage does not start at 0 (found {first_start}).")

        # Check that the last ends at audio_duration
        last_end = sorted_footages[-1]["end"]
        if abs(last_end - audio_duration) > 1e-6:
            raise ValueError(f"Last footage does not end at audio_duration ({audio_duration}). Found {last_end}.")

        # Check consecutive footages for no gap
        for i in range(len(sorted_footages) - 1):
            this_end = sorted_footages[i]["end"]
            next_start = sorted_footages[i + 1]["start"]
            # must match exactly within a small tolerance
            if abs(this_end - next_start) > 1e-6:
                raise ValueError(
                    f"Gap found between footage[{i}] ending at {this_end} and footage[{i + 1}] starting at {next_start}."
                )

        #####################################################################
        # 3) Create snippet clips for each footage
        #####################################################################

        def resolve_media_path(file_name: str):
            return os.path.abspath(os.path.join(self.media_dir, file_name))

        snippet_paths = []
        for i, f in enumerate(sorted_footages):
            ftype = f["type"]  # "video" or "photo"
            fname = resolve_media_path(f["filename"])
            start_t = f["start"]
            end_t = f["end"]

            segment_duration = end_t - start_t
            if segment_duration <= 0:
                raise ValueError(f"Invalid segment duration for {fname}, start={start_t}, end={end_t}.")

            snippet_path = os.path.join(self.output_dir, f"snippet_{i + 1}.mp4")

            if ftype == "video":
                # We'll clip exactly segment_duration from the start of that file
                # (assuming the source is long enough).
                ffmpeg.format_youtube_short_video(
                    video_path=fname,
                    clip_length=segment_duration,
                    video_encoder=h264_encoder,
                    output_path=snippet_path
                )
            else:  # "photo"
                # We'll create a short clip of exactly 1 second if GPT said so,
                # but the logic says (end - start)=1 anyway.
                # We'll just do the same approach but with a helper for photos:
                # ffmpeg.create_photo_clip(
                #     photo_path=fname,
                #     clip_length=segment_duration,
                #     encoder=h264_encoder,
                #     output_path=snippet_path
                # )

                warnings.warn("Photo clips are not supported yet. Skipping photo clip creation.")

            snippet_paths.append(snippet_path)

        #####################################################################
        # 4) Concatenate them in sequence
        #####################################################################
        # Because we have verified no gaps, we can simply do end-to-end concat.
        # The total length = audio_duration.
        # If any mismatch occurs, we would have thrown an error above.
        start = time.time()
        concat_cmd = ffmpeg.build_concat_cmd(snippet_paths, concat_timeline_path)
        subprocess.run(concat_cmd, check=True)
        end = time.time()
        print(f"✅ Combined {len(snippet_paths)} snippet footages into one, took {end - start} sec.")

        #####################################################################
        # 5) Add subtitles
        #####################################################################
        start = time.time()
        subs.add_subtitles(concat_timeline_path, sentences, audio_duration, concat_with_subs)
        end = time.time()
        print(f"✅ Added subtitles to the video, took {end - start} sec.")

        #####################################################################
        # 6) Add the speech
        #####################################################################
        start = time.time()
        ffmpeg.add_audio(concat_with_subs, speech_path, h264_encoder, concat_with_speech)
        end = time.time()
        print(f"✅ Added voice to the video, took {end - start} sec.")

        #####################################################################
        # 7) Add background music
        #####################################################################
        start = time.time()
        ffmpeg.mix_background_audio(concat_with_speech, music_path, output_path)
        end = time.time()
        print(f"✅ Added background music to the video, took {end - start} sec.")

        #####################################################################
        # 8) Cleanup
        #####################################################################
        for snippet in snippet_paths:
            os.remove(snippet)
        os.remove(concat_timeline_path)
        os.remove(concat_with_speech)

        total_time = time.time() - edit_start
        print(f"✅ Edited the YouTube shorts video in {total_time:.2f} sec.")

        return output_path

    def generate_script(self, prompt: str) -> str:
        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": "You are an AI agent for that produces short video scripts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )

        # Extract the content of the response
        script = response.choices[0].message.content.strip()

        # Save to file
        with open(os.path.join(self.output_dir, 'script_1st_shot.txt'), 'w') as f:
            f.write(script)

        print(f"✅ Generated script using {self.openai_model} (1st shot)")
        return script

    def generate_script_2nd_shot(self, prompt) -> str:
        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": "You are an AI agent for that enhances short video scripts."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=800
        )

        # Extract the content of the response
        script = response.choices[0].message.content.strip()

        # Save to file
        with open(os.path.join(self.output_dir, 'script_2nd_shot.txt'), 'w') as f:
            f.write(script)

        print(f"✅ Enhanced the script using {self.openai_model} (2nd shot)")
        return script

    def generate_script_with_footages(self, prompt):
        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": "You are an AI agent that picks footages for YouTube shorts."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=800
        )

        # Extract the content of the response
        script = response.choices[0].message.content.strip()


        # Save to file
        with open(os.path.join(self.output_dir, 'script_with_footages.txt'), 'w') as f:
            f.write(script)

        print(f"✅ Generated script with footages using {self.openai_model}")
        return script

    def text_to_speech(self, script) -> (str, list, list):
        audio = self.elevenlabs_client.text_to_speech.convert_with_timestamps(
            text=script,
            # Liam
            voice_id="TX3LPaxmHKxFdv7VOQHJ",
            model_id="eleven_multilingual_v2",
            output_format='mp3_44100_128',
            voice_settings=VoiceSettings(stability=0.71, similarity_boost=0.5, style=0.0, use_speaker_boost=True)
        )

        output_file = self.output_dir + '/elevenlabs_script.mp3'

        audio_bytes = base64.b64decode(audio["audio_base64"])
        alignment = audio['alignment']

        words = subs.group_chars_into_words(
            alignment['characters'],
            alignment['character_start_times_seconds'],
            alignment['character_end_times_seconds']
        )
        sentences = subs.group_words_into_sentences(words)

        timestamps_dict_path = os.path.join(self.output_dir, 'eleven_labs_timestamps.json')
        with open(timestamps_dict_path, 'w') as f:
            json_str = json.dumps(alignment, indent=4)
            f.write(json_str)

        # Write the audio data to a file
        with open(output_file, "wb") as f:
            f.write(audio_bytes)

        print("✅ Generated speech using Eleven Labs")

        return output_file, words, sentences

    @staticmethod
    def get_footages(script: str, words: list[Dict]):
        return parse_and_time_script(script, words)
