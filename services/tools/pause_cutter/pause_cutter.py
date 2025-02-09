import os.path

import whisper

from services.pipelines import ffmpeg
from services.pipelines.pause_detector import detect_pauses


class PauseCutter:
    working_dir: str = None

    whisper: whisper.Whisper

    def __init__(self, working_dir: str, whisper_model: str = "small"):
        self.working_dir = working_dir

        self.whisper = whisper.load_model(whisper_model)

    def run(self, video_name: str,output_name: str, pause_threshold=0.5, pad=0.1):
        video_encoder = ffmpeg.get_gpu_accelerated_h264_encoder()
        if video_encoder is None:
            video_encoder = "libx264"
        audio_encoder = ffmpeg.get_gpu_accelerated_aac_encoder()
        if audio_encoder is None:
            audio_encoder = "aac"

        transcription = self.whisper.transcribe(
            audio=os.path.join(self.working_dir, 'input', 'videos', video_name),
            word_timestamps=True
        )

        _, pauses = detect_pauses(get_word_timings(transcription), threshold=pause_threshold, pad=pad)

        ffmpeg.trim_pauses_from_media(
            media_path=os.path.join(self.working_dir, 'input', 'videos', video_name),
            pauses=pauses,
            output_path=os.path.join(self.working_dir, 'output', output_name),
            video_codec=video_encoder,
            audio_codec=audio_encoder
        )


def get_word_timings(result):
    word_timings = []
    segments = result["segments"]
    for segment in segments:
        words = segment["words"]
        for word in words:
            word_timings.append({
                "start": word["start"],
                "end": word["end"],
                "word": word["word"]
            })

    return word_timings
