import base64
import json
import os
import subprocess
import time

import elevenlabs
import openai
from elevenlabs import VoiceSettings

from elevenlabs.client import ElevenLabs

import requests
from openai import OpenAI

from services.shorts_pipeline.ass import generate_ass_with_highlights, group_characters_into_words
from services.shorts_pipeline.ffmpeg import build_concat_cmd, get_gpu_accelerated_h264_encoder
from services.shorts_pipeline.file_utils import download_file
from services.shorts_pipeline.script_parser import get_tags_from_script
from services.shorts_pipeline.srt import generate_srt


class ShortVideoPipeline:
    pexels_api_key: str = None

    openai_model = 'gpt-4o'
    openai_client = openai.OpenAI

    elevenlabs_client: elevenlabs.ElevenLabs = None

    pexels_api_url = 'https://api.pexels.com'

    output_dir = './output'
    media_dir = './media'

    max_footages = 12
    min_footage_duration = 8

    def __init__(self, open_api_key: str, elevenlaps_api_key: str, pexels_api_key: str):
        self.pexels_api_key = pexels_api_key
        self.openai_client = OpenAI(
            api_key=open_api_key,
        )
        self.elevenlabs_client = ElevenLabs(api_key=elevenlaps_api_key)

        os.makedirs(self.output_dir, exist_ok=True)

    def run(self, script_prompt, script_2nd_shot_prompt, footage_prompt: str) -> str:
        start = time.time()

        script = self.generate_script(script_prompt)
        print(f"✅ Generated script using {self.openai_model}")

        script_2nd_shot = self.generate_script_2nd_shot(script_2nd_shot_prompt, script)

        speech_file_path, subtitles_path = self.text_to_speech(script)
        footage_file_paths = self.get_footage_for_tags([])

        output_path = self.create_video(speech_file_path, subtitles_path, footage_file_paths)

        end = time.time()

        print(f"⌛ Generated a video in {end - start} seconds")

        return output_path

    def create_video(self, speech_path: str, subs_path: str, footage_paths: list[str]) -> str:
        edit_start = time.time()

        # Ensure all paths are absolute
        speech_path = os.path.abspath(speech_path)
        footage_paths = [os.path.abspath(path) for path in footage_paths]
        concat_video_path = os.path.join(self.output_dir, 'concat.mp4')
        concat_with_speech_and_subs_path = os.path.join(self.output_dir, 'concat_with_speech_and_subs.mp4')
        output_path = os.path.join(self.output_dir, 'output.mp4')
        music_path = os.path.join(self.media_dir, 'uplifting_1.mp3')
        subs_path = os.path.abspath(subs_path)

        h264_encoder = get_gpu_accelerated_h264_encoder()
        if h264_encoder is None:
            h264_encoder = 'libx264'

        try:
            # Step 1: Check the duration of the audio file
            audio_duration_str = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries',
                    'format=duration',
                    '-of',
                    'default=noprint_wrappers=1:nokey=1',
                    speech_path
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            audio_duration = float(audio_duration_str.stdout.strip())

            print(f"Voice duration is {audio_duration} sec.")
        except subprocess.CalledProcessError as e:
            raise ValueError(e.stderr)

        # Step 2: Calculate the duration for each video
        num_videos = len(footage_paths)
        segment_duration = audio_duration / num_videos

        normalized_videos = []

        # Step 3: Resize and cut the videos
        for i, video_path in enumerate(footage_paths):
            start = time.time()

            normalized_video_path = os.path.abspath(os.path.join(self.output_dir, f'normalized_video_{i + 1}.mp4'))
            normalize_cmd = [
                "ffmpeg", '-y',
                "-loglevel", "error",
                '-i', video_path,
                "-t", str(segment_duration),
                '-vf', 'scale=1080:1920',
                '-c:v', h264_encoder,
                '-crf', '23',
                '-preset', 'ultrafast',
                '-an',
                normalized_video_path
            ]
            subprocess.run(normalize_cmd, check=True)
            normalized_videos.append(normalized_video_path)

            end = time.time()

            print(
                f"ℹ️ Normalized video {os.path.basename(video_path)} to 1080x1920 and trimmed, took {end - start} sec.")

        # Step 5: Concatenate the normalized videos
        try:
            start = time.time()
            concat_cmd = build_concat_cmd(normalized_videos, concat_video_path)
            subprocess.run(concat_cmd, check=True)
            end = time.time()

            print(f"✅ Combined {len(normalized_videos)} video footages into one, took {end - start} sec.")
        except subprocess.CalledProcessError as e:
            raise ValueError(e.stderr, e.stdout)

        # Step 6: Add voice and subtitles to the video
        try:
            start = time.time()

            cmd = [
                "ffmpeg", '-y',
                "-loglevel", "warning",
                '-hide_banner',
                '-i', concat_video_path,
                '-i', speech_path,
                '-map', '0:v', '-map', '1:a',
                '-vf', f'ass={subs_path}',
                '-c:v', h264_encoder,
                '-b:v', '5M',
                '-c:a', 'aac',
                concat_with_speech_and_subs_path
            ]
            subprocess.run(cmd, check=True)

            end = time.time()

            print(f"✅ Added voice and subtitles to the video, took {end - start} sec.")
        except subprocess.CalledProcessError as e:
            raise ValueError(e.stderr, e.stdout)

        # Step 7: Add background music to the video
        try:
            start = time.time()

            cmd = [
                "ffmpeg", '-y',
                '-hide_banner',
                "-loglevel", "error",
                '-i', concat_with_speech_and_subs_path,
                '-i', music_path,
                '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=shortest[a]',
                '-map', '0:v',
                '-map', '[a]',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                output_path
            ]
            subprocess.run(cmd, check=True)

            end = time.time()

            print(f"✅ Added background music to the video, took {end - start} sec.")
        except subprocess.CalledProcessError as e:
            raise ValueError(e.stderr, e.stdout)

        # Delete temporary files
        for file in normalized_videos:
            os.remove(file)
        os.remove(concat_video_path)
        os.remove(concat_with_speech_and_subs_path)

        end = time.time()
        print(f"✅ Edited the YouTube shorts video in {end - edit_start} sec.")

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
        return script

    def generate_script_2nd_shot(self, prompt, script: str) -> str:
        prompt = prompt.format(script=script)

        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": "You are an AI agent for that produces short video scripts."},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": script}
            ],
            temperature=0.7,
            max_tokens=800
        )

        # Extract the content of the response
        script = response.choices[0].message.content.strip()
        return script


    def text_to_speech(self, script) -> (str, str):
        timestamps_dict_path = os.path.join(self.output_dir, 'eleven_labs_ts_dict.json')
        subtitiles_path = os.path.join(self.output_dir, 'subtitles.ass')

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

        generate_ass_with_highlights(alignment, subtitiles_path)
        print(f"✅ ASS subtitles saved to {subtitiles_path}")

        # Mostly for debugging and testing
        with open(timestamps_dict_path, 'w') as f:
            json_str = json.dumps(alignment, indent=4)
            f.write(json_str)

        # Write the audio data to a file
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        print(f"✅ Elevenlabs text-to-speech saved to {output_file}")

        return output_file, subtitiles_path

    def get_footage_for_tags(self, tags: list[str]) -> list[str]:
        output_files = []

        unique_videos_lookup = {}

        for tag in tags:
            search_url = self.pexels_api_url + '/videos/search'
            response = requests.get(
                url=search_url,
                headers={
                    'Authorization': self.pexels_api_key
                },
                params={
                    'query': tag,
                    'orientation': 'portrait',
                    'size': 'large',
                    'per_page': 5
                }
            )

            if response.status_code != 200:
                raise ValueError(f"request to elevenlabs failed with status code {response.status_code}")

            data = response.json()

            videos = data['videos']
            if len(videos) == 0:
                raise ValueError(f"elevenlabs returned 0 videos for tag {tag}")

            for i, video in enumerate(videos):
                if len(output_files) >= self.max_footages:
                    break

                if video['duration'] < self.min_footage_duration:
                    continue

                file_url = video['video_files'][0]['link']
                if file_url in unique_videos_lookup:
                    continue
                unique_videos_lookup[file_url] = True

                save_path = self.output_dir + f"/pexels_footage_{tag}_{i}.mp4"

                download_file(file_url, save_path)

                print(f'ℹ️ Downloaded video footage for topic: {tag}')

                output_files.append(save_path)

        return output_files
