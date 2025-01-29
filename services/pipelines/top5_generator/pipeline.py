import base64
import hashlib
import json
import logging
import math
import os
import time
import uuid

from elevenlabs import ElevenLabs, VoiceSettings

import services.pipelines.subtitles as subs
import services.pipelines.top5_generator.script_parser as parser
import services.pipelines.top5_generator.ffmpeg as top5_ffmpeg
import services.pipelines.ffmpeg as ffmpeg
import services.pipelines.pause_detector as pause


class TOP5PipelineConfig:
    background_video: str = None
    background_music: str = None
    video_effect: str = None

    places_videos: list[str] = []

    def __init__(self, background_video: str, background_music: str, video_effect: str, places_videos: list[str]):
        self.background_video = background_video
        self.background_music = background_music
        self.video_effect = video_effect
        self.places_videos = places_videos

    def validate(self):
        if not self.video_effect or not self.background_video or not self.background_music:
            raise ValueError("Missing required configuration")

        if not self.video_effect.endswith('.mp4'):
            raise ValueError("Video effect must be an MP4 file")

        if not self.background_video.endswith('.mp4'):
            raise ValueError("Background video must be an MP4 file")

        if not self.background_music.endswith('.mp3') and not self.background_music.endswith('.mp4'):
            raise ValueError("Background music must be an MP3 or MP4 file")


class TOP5Pipeline:
    elevenlabs_client: ElevenLabs = None

    logger: logging.Logger = None

    config: TOP5PipelineConfig = None

    working_dir: str = None

    def __init__(self, logger: logging.Logger, config: TOP5PipelineConfig, elevenlaps_api_key: str, working_dir: str):
        self.elevenlabs_client = ElevenLabs(api_key=elevenlaps_api_key)
        self.working_dir = working_dir
        self.logger = logger
        self.config = config

    def assert_working_dir(self):
        if not os.path.exists(self.working_dir):
            raise FileNotFoundError(f"Working directory not found: {self.working_dir}")

        background_video = os.path.join(self.working_dir, 'input', 'videos', self.config.background_video)

        background_music = os.path.join(self.working_dir, 'input', 'music', self.config.background_music)
        effect = os.path.join(self.working_dir, 'input', 'video_effects', self.config.video_effect)
        videos = [os.path.join(self.working_dir, 'input', 'videos', video) for video in self.config.places_videos]

        if not os.path.exists(background_video):
            raise FileNotFoundError(f"Background video not found: {background_video}")

        if not os.path.exists(background_music):
            raise FileNotFoundError(f"Background music not found: {background_music}")

        if not os.path.exists(effect):
            raise FileNotFoundError(f"Video effect not found: {effect}")

        for video_name in videos:
            if not os.path.exists(video_name):
                raise FileNotFoundError(f"Places video not found: {video_name}")

    def run(self,
            script: str,
            subtitle_color: str = 'white',
            subtitle_highlight_color: str = '#7710e2',
            background_music_volume_adjustment: int = -25
            ):

        start = time.time()

        self.assert_working_dir()

        background_video_path = os.path.join(self.working_dir, 'input', 'videos', self.config.background_video)
        background_music_name = os.path.join(self.working_dir, 'input', 'music', self.config.background_music)
        effect_path = os.path.join(self.working_dir, 'input', 'video_effects', self.config.video_effect)
        video_names = [os.path.join(self.working_dir, 'input', 'videos', video) for video in self.config.places_videos]

        h264_encoder = ffmpeg.get_gpu_accelerated_h264_encoder()
        if h264_encoder is None:
            h264_encoder = 'libx264'

        # 2. Generate speech using Eleven Labs
        speech_file, words = self.text_to_speech(script)

        # 3. Detect pauses and split the script into sentences
        words, pauses = pause.detect_pauses(
            words,
            threshold=0.4,
            pad=0.075
        )
        self.logger.info(f"ℹ️ Detected {len(pauses)} pauses")

        # 4. Trim the pauses
        no_pauses_file = os.path.join(self.working_dir, 'output', 'no_pauses_speech.mp4')
        ffmpeg.trim_pauses_from_media(speech_file, pauses, no_pauses_file)

        # 5. Build the sentences
        sentences = subs.group_words_into_sentences(words)

        # 6. Parse the script and get footage segments
        footage_segments = parser.get_footage_segments(script, words, video_names)

        # 7.  Check the length of the background video, if it is not long enough, loop it
        background_video_duration = ffmpeg.get_media_duration(background_video_path)
        if background_video_duration < footage_segments['script_end']:
            looped_background_path = os.path.join(self.working_dir, 'output', 'looped_background.mp4')
            ffmpeg.loop_video(
                video_path=background_video_path,
                output_path=looped_background_path,
                loop_count=math.ceil(footage_segments['script_end'] / background_video_duration),
            )
            background_video_path = looped_background_path
            self.logger.info("✅ Looped background video to match the script duration")

        # 8. Create audio-less edit
        video_edit_path = os.path.join(self.working_dir, 'output', 'video_edit.mp4')
        self.overlay_footages(
            video_segments=footage_segments['segments'],
            background_video_path=background_video_path,
            output_path=video_edit_path,
            video_encoder=h264_encoder,
            duration=footage_segments['script_end']
        )

        # 9. Add speech to the edit
        with_speech_path = os.path.join(self.working_dir, 'output', 'video_with_speech.mp4')
        ffmpeg.add_audio(
            video_path=video_edit_path,
            audio_path=no_pauses_file,
            encoder=h264_encoder,
            output_path=with_speech_path
        )
        self.logger.info("✅ Added speech to the edit")

        # 10. Add subtitles to the edit
        with_subtitles_path = os.path.join(self.working_dir, 'output', 'video_with_subtitles.mp4')
        subs.add_subtitles(
            video_path=with_speech_path,
            sentences=sentences,
            video_duration=footage_segments['script_end'],
            output_path=with_subtitles_path,
            highlight_color=subtitle_highlight_color,
            color=subtitle_color
        )
        self.logger.info("✅ Generated video with subtitles")

        # 11. Add background music to the edit
        with_music_path = os.path.join(self.working_dir, 'output', 'video_with_music.mp4')
        ffmpeg.mix_background_audio(
            video_path=with_subtitles_path,
            audio_path=background_music_name,
            output_path=with_music_path,
            volume_adjustment=background_music_volume_adjustment
        )

        # 12. Add effects to the edit
        with_effects_path = os.path.join(self.working_dir, 'output', 'video_with_effects.mp4')
        ffmpeg.overlay_effect(
            video_path=with_music_path,
            effect_path=effect_path,
            blend_mode='lignten',
            opacity=0.2,
            video_encoder=h264_encoder,
            output_path=with_effects_path
        )

        self.logger.info("✅ Added background music to the edit")

        end = time.time()

        self.logger.info(f"⌛ Generated a video in {end - start} seconds")

    def overlay_footages(self, video_segments: list[dict[str, any]], background_video_path: str, output_path: str,
                         duration: float,
                         video_encoder: str):
        background_video_fmt_path = os.path.join(os.path.dirname(output_path), 'background_fmt.mp4')
        ffmpeg.format_youtube_short_video(
            video_path=background_video_path,
            clip_length=duration,
            video_encoder=video_encoder,
            output_path=background_video_fmt_path
        )
        self.logger.info("✅ Formatted background video")

        fmt_segments: list[dict[str, any]] = []
        for segment in video_segments:
            fmt_segment_path = os.path.join(os.path.dirname(output_path), f'{uuid.uuid4().hex}.mp4')
            ffmpeg.format_youtube_short_video(
                video_path=segment['footage'],
                clip_length=segment['end'] - segment['start'],
                video_encoder=video_encoder,
                output_path=fmt_segment_path
            )
            self.logger.info(f"✅ Formatted video segment: {segment['footage']}")

            fmt_segments.append({
                "footage": fmt_segment_path,
                "start": segment['start'],
                "end": segment['end']
            })

        top5_ffmpeg.overlay_videos(
            background_footage_path=background_video_fmt_path,
            footages=fmt_segments,
            output_path=output_path,
            video_encoder=video_encoder
        )

        self.logger.info("✅ Overlayed video footages")

        os.remove(background_video_fmt_path)
        for segment in fmt_segments:
            os.remove(segment['footage'])

    def text_to_speech(self, script) -> (str, list[dict]):
        """
        Convert text to speech via ElevenLabs, with caching based on the script hash.
        Returns:
          - speech_file: path to the generated (or cached) speech file (.mp3)
          - words: list of word-level data
          - sentences: list of sentence-level data
        """

        # ------------------------------------------------------
        # 1) Compute a hash of the script to identify duplicates
        # ------------------------------------------------------
        script_hash = hashlib.md5(script.encode('utf-8')).hexdigest()

        speech_file = os.path.join(
            self.working_dir,
            'output',
            f"eleven_labs_speech_{script_hash}.mp3"
        )
        alignment_file = os.path.join(
            self.working_dir,
            'output',
            f"eleven_labs_alignment_{script_hash}.json"
        )

        # ----------------------------------------------------------------
        # 2) Check if cached files exist. If yes, reuse them; if not, call TTS
        # ----------------------------------------------------------------
        if os.path.exists(speech_file) and os.path.exists(alignment_file):
            self.logger.info(f"✅ Using cached ElevenLabs speech for hash: {script_hash}")

            # Read alignment JSON
            with open(alignment_file, 'r') as f:
                alignment = json.load(f)

            # Reconstruct the words and sentences from alignment
            words = subs.group_chars_into_words(
                alignment['characters'],
                alignment['character_start_times_seconds'],
                alignment['character_end_times_seconds']
            )
            sentences = subs.group_words_into_sentences(words)

        else:
            self.logger.info("⌛ No cached version found. Generating fresh speech using ElevenLabs...")

            # 3) Call ElevenLabs for TTS
            audio = self.elevenlabs_client.text_to_speech.convert_with_timestamps(
                text=script,
                voice_id="TX3LPaxmHKxFdv7VOQHJ",  # example: "Liam"
                model_id="eleven_multilingual_v2",
                output_format='mp3_44100_128',
                voice_settings=VoiceSettings(
                    stability=0.71,
                    similarity_boost=0.5,
                    style=0.0,
                    use_speaker_boost=True
                )
            )

            # 4) Write MP3 file
            audio_bytes = base64.b64decode(audio["audio_base64"])
            with open(speech_file, "wb") as f:
                f.write(audio_bytes)

            # 5) Process alignment
            alignment = audio['alignment']
            with open(alignment_file, 'w') as f:
                json_str = json.dumps(alignment)
                f.write(json_str)

            # 6) Build words & sentences
            words = subs.group_chars_into_words(
                alignment['characters'],
                alignment['character_start_times_seconds'],
                alignment['character_end_times_seconds']
            )
            self.logger.info("✅ Generated new speech and alignment from ElevenLabs")

        # Return paths and data
        return speech_file, words
