import os.path

from services.pipelines import ffmpeg


class VideoUnifier:
    working_dir: str = None

    def __init__(self, working_dir: str):
        self.working_dir = working_dir

    def unify(self, video_name: str, effect_name: str, output_name: str, blend_mode: str, opacity: float):
        video_encoder = ffmpeg.get_gpu_accelerated_h264_encoder()
        if video_encoder is None:
            video_encoder = "libx264"

        ffmpeg.overlay_effect_with_scaling(
            video_path=os.path.join(self.working_dir, 'input', 'videos', video_name),
            effect_path=os.path.join(self.working_dir, 'input', 'video_effects', effect_name),
            output_path=os.path.join(self.working_dir, 'output', output_name),
            blend_mode=blend_mode,
            opacity=opacity,
            video_encoder=video_encoder
        )
