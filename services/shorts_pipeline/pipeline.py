import base64
import os
import subprocess

import elevenlabs
import openai

from elevenlabs.client import ElevenLabs

import requests
from openai import OpenAI

from services.shorts_pipeline.ffmpeg import build_concat_cmd
from services.shorts_pipeline.file_utils import download_file
from services.shorts_pipeline.script_parser import get_tags_from_script
from services.shorts_pipeline.srt import generate_srt


class ShortVideoPipeline:
    pexels_api_key: str = None

    openai_model = 'gpt-4o'
    open_ai_temperature = 0.7
    openai_max_tokens = 500
    openai_client = openai.OpenAI

    elevenlabs_voice = 'Brian'
    elevenlabs_model = 'eleven_multilingual_v2'
    elevenlabs_output_format = 'mp3_44100_128'
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

    def run(self, script_promts: str)-> str:
        script, tags = self.generate_script(script_promts)

        speech_file_path, srt_file = self.text_to_speech(script)
        footage_file_paths = self.get_footage_for_tags(tags)

        output_path = self.create_video(speech_file_path, srt_file, footage_file_paths)
        return output_path

    def create_video(self, speech_path: str, subs_path: str, footage_paths: list[str]) -> str:
        # Ensure all paths are absolute
        speech_path = os.path.abspath(speech_path)
        footage_paths = [os.path.abspath(path) for path in footage_paths]
        concat_video_path = os.path.join(self.output_dir, 'concat.mp4')
        concat_with_speech_and_subs_path = os.path.join(self.output_dir, 'concat_with_speech_and_subs.mp4')
        output_path = os.path.join(self.output_dir, 'output.mp4')
        music_path = os.path.join(self.media_dir, 'uplifting_1.mp3')
        subs_path = os.path.abspath(subs_path)

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
        except subprocess.CalledProcessError as e:
            raise ValueError(e.stderr)

        # Step 2: Calculate the duration for each video
        num_videos = len(footage_paths)
        segment_duration = audio_duration / num_videos

        trimmed_videos = []
        normalized_videos = []

        for i, video_path in enumerate(footage_paths):
            # Step 3: Normalize and cut the video
            normalized_video_path = os.path.abspath(os.path.join(self.output_dir, f'normalized_video_{i + 1}.mp4'))
            normalize_cmd = [
                "ffmpeg", '-y',
                '-i', video_path,
                "-t", str(segment_duration),
                '-vf', 'scale=1080:1920',
                '-c:v', 'libx264',
                '-crf', '23',
                '-an',
                normalized_video_path
            ]
            subprocess.run(normalize_cmd, check=True)
            normalized_videos.append(normalized_video_path)

        # Step 5: Concatenate the normalized videos
        try:
            concat_cmd = build_concat_cmd(normalized_videos, concat_video_path)
            subprocess.run(concat_cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise ValueError(e.stderr, e.stdout)

        # Step 6: Add dubbing and subtitles to the video
        try:
            cmd = [
                "ffmpeg", '-y',
                '-i', concat_video_path,
                '-i', speech_path,
                '-map', '0:v', '-map', '1:a',
                '-vf', f'subtitles={subs_path}',
                concat_with_speech_and_subs_path
            ]
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise ValueError(e.stderr, e.stdout)

        # Step 7: Add background music to the video
        try:
            cmd = [
                "ffmpeg", '-y',
                '-i', concat_with_speech_and_subs_path,
                '-i', music_path,
                '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=shortest[a]',
                '-map', '0:v', '-map', '[a]',
                output_path
            ]
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise ValueError(e.stderr, e.stdout)

        # Delete footage video files after the merge
        for file in footage_paths:
            os.remove(file)

        # Delete trimmed video files
        for file in trimmed_videos:
            os.remove(file)

        for file in normalized_videos:
            os.remove(file)

        os.remove(concat_video_path)

        # The final output video with speech is now at output_path
        return output_path

    def generate_script(self, prompt: str) -> (str, list[str]):
        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates short video scripts."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.open_ai_temperature,
            max_tokens=self.openai_max_tokens
        )

        # Extract the content of the response
        script = response.choices[0].message.content.strip()
        tags = get_tags_from_script(script)

        return script.split('#####')[0], tags

    def text_to_speech(self, script) -> (str, str):
        audio = self.elevenlabs_client.text_to_speech.convert_with_timestamps(
            text=script,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id=self.elevenlabs_model,
            output_format=self.elevenlabs_output_format
        )

        output_file = self.output_dir + '/elevenlabs_script.mp3'

        audio_bytes = base64.b64decode(audio["audio_base64"])

        alignment = audio['alignment']
        srt = generate_srt(script, alignment)

        srt_file = os.path.join(self.output_dir, 'subtitles.srt')

        # Write the audio data to a file
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        print(f"[DEBUG] Elevenlabs text-to-speech saved to {output_file}")

        with open(srt_file, 'w') as f:
            f.write(srt)
        print(f"[DEBUG] Saved the subtitles to {srt_file}")

        return output_file, srt_file

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

                print(f'[DEBUG] Downloaded video footage for tag {tag}')

                output_files.append(save_path)

        return output_files
