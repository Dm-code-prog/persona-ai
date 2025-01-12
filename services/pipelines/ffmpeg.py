import shlex
import subprocess
import platform


def build_concat_cmd(input_file_paths: list[str], output_file_path: str) -> list[str]:
    h264_encoder = get_gpu_accelerated_h264_encoder()
    if h264_encoder is None:
        h264_encoder = 'libx264'

    # Base command
    command = ["ffmpeg"]

    n = len(input_file_paths)

    # Build the filter_complex input segments for the concat filter
    # e.g. "[0:v][1:v][2:v]...concat=n=3:v=1[outv]"
    input_segments = "".join([f"[{i}:v]" for i in range(n)])
    filter_complex = f"{input_segments}concat=n={n}:v=1[outv]"

    # Add the input files
    for i, file_path in enumerate(input_file_paths):
        command.extend(["-i", file_path])

    # Add the filter_complex and the rest of the parameters
    command.extend([
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", h264_encoder,
        "-crf", "23",
        "-y",
        "-loglevel", "error",
        output_file_path
    ])

    # Join into a single command string
    return command


def get_gpu_accelerated_h264_encoder():
    """
    Detects the available H.264 GPU-accelerated encoder on the current platform.

    Returns:
        str: The name of the GPU-accelerated H.264 encoder, or None if not found.
    """
    try:
        # Run FFmpeg to list all encoders
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            check=True
        )

        encoders = result.stdout.splitlines()
        gpu_encoders = []

        # Check OS to identify GPU-specific encoders
        os_name = platform.system()

        if os_name == "Darwin":  # macOS
            search_terms = ["h264_videotoolbox"]
        elif os_name == "Windows":  # Windows
            search_terms = ["h264_nvenc", "h264_qsv", "h264_amf"]
        elif os_name == "Linux":  # Linux
            search_terms = ["h264_vaapi", "h264_nvenc", "h264_qsv"]
        else:
            print("Unsupported Operating System.")
            return None

        # Look for GPU-accelerated encoders in the output
        for line in encoders:
            if any(term in line for term in search_terms):
                encoder_name = line.split()[1]
                gpu_encoders.append(encoder_name)

        if gpu_encoders:
            print(f"✅ GPU-Accelerated H.264 Encoder(s) Found: {', '.join(gpu_encoders)}")
            return gpu_encoders[0]  # Return the first found GPU encoder
        else:
            print("❌ No GPU-accelerated H.264 encoder found.")
            return None

    except subprocess.CalledProcessError as e:
        print(f"Error running FFmpeg: {e}")
        return None
    except FileNotFoundError:
        print("❌ FFmpeg is not installed or not in PATH.")
        return None


def get_media_duration(file_path: str) -> float:
    """
    Get the duration of a media file using FFprobe.

    Args:
        file_path (str): The path to the media file.

    Returns:
        float: The duration of the media file in seconds.
    """

    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=noprint_wrappers=1:nokey=1',
        file_path
    ]

    print("Running ffmpeg:\n", " ".join(shlex.quote(arg) for arg in cmd))

    try:
        # Run FFprobe to get media file info
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        # Parse duration from the output
        duration = float(result.stdout.strip())
        return duration

    except subprocess.CalledProcessError as e:
        print(f"Error running FFprobe: {e}")
        return 0
    except FileNotFoundError:
        print("❌ FFprobe is not installed or not in PATH.")
        return 0


def format_youtube_short_video(video_path: str, clip_length: float, video_encoder: str, output_path: str):
    """
    Normalized (scales, cuts, and encodes) a video to fit the YouTube Shorts format (1080x1920).

    :param video_path:  Path to the video file
    :param clip_length:  Length of the clip in seconds to cut
    :param video_encoder:  The encoder to use, preferably a GPU accelerated one, like video_toolbox for Mac
    :param output_path:  Path where to save the output video
    :return: None
    """

    # 1) Get the duration of the input video
    video_duration = get_media_duration(video_path)
    # 2) Raise an error if the video is shorter than the requested clip_length
    if video_duration < clip_length:
        raise ValueError(
            f"Requested clip_length ({clip_length}s) is greater than video duration ({video_duration:.2f}s) "
            f"for '{video_path}'."
        )

    # 3) Run ffmpeg to scale, cut, and encode
    try:
        cmd = [
            "ffmpeg", '-y',
            '-hide_banner',
            "-loglevel", "warning",
            '-i', video_path,
            "-t", str(clip_length),
            '-vf', 'crop=(9/16*ih):ih,scale=1080:1920',
            '-b:v', '8M',
            '-r', '30',
            '-c:v', video_encoder,
            '-an',
            output_path
        ]

        print("Running ffmpeg:\n", " ".join(shlex.quote(arg) for arg in cmd))

        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg command failed with error: {e.stderr}")


def add_audio(video_path, audio_path, encoder, output_path: str):
    """
    Add audio to a video file.

    :param video_path:  Path to the video file
    :param audio_path:  Path to the audio file
    :param encoder:  The encoder to use, preferably a GPU accelerated one, like video_toolbox for Mac
    :param output_path:  Path where to save the output video
    :return: None
    """
    try:
        cmd = [
            "ffmpeg", '-y',
            "-loglevel", "warning",
            '-hide_banner',
            '-stats',
            '-i', video_path,
            '-i', audio_path,
            '-map', '0:v', '-map', '1:a',
            '-c:v', encoder,
            '-b:v', '5M',
            '-c:a', 'aac',
            output_path
        ]

        print("Running ffmpeg:\n", " ".join(shlex.quote(arg) for arg in cmd))

        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg command failed with error: {e.stderr}")


def mix_background_audio(video_path, audio_path, output_path: str, volume_adjustment: int = -25):
    """
    Mixes an audio file with a video file.

    :param volume_adjustment:
    :param video_path:  Path to the video file
    :param audio_path:  Path to the audio file
    :param output_path:  Path where to save the output video
    :return: None
    """
    try:
        cmd = [
            "ffmpeg", '-y',
            '-hide_banner',
            "-loglevel", "error",
            '-i', video_path,  # background video (with its audio)
            '-i', audio_path,  # external audio
            '-filter_complex',
            # 1) Volume-filter the second input -> [vol2]
            # 2) Mix the unmodified 0:a and [vol2] with amix -> [a]
            f"[1:a]volume=-{volume_adjustment}dB[vol2]; [0:a][vol2]amix=inputs=2:duration=shortest[a]",
            '-map', '0:v',  # keep the original video
            '-map', '[a]',  # map the mixed audio
            '-c:v', 'copy',  # copy the video without re-encoding
            '-c:a', 'aac',  # encode audio as AAC
            '-b:a', '192k',
            output_path
        ]

        print("Running ffmpeg:\n", " ".join(shlex.quote(arg) for arg in cmd))

        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg command failed with error: {e.stderr}")


def loop_video(video_path: str, loop_count: int, output_path: str):
    """
    Loop a video a specified number of times.

    :param video_path:  Path to the video file
    :param loop_count:  Number of times to loop the video
    :param output_path:  Path where to save the output video
    :return: None
    """
    try:
        cmd = [
            "ffmpeg", '-y',
            '-hide_banner',
            "-loglevel", "error",
            '-stream_loop', str(loop_count),
            '-i', video_path,
            '-c', 'copy',
            output_path
        ]

        print("Running ffmpeg:\n", " ".join(shlex.quote(arg) for arg in cmd))

        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg command failed with error: {e.stderr}")


def trim_pauses_from_audio(
        audio_file_path: str,
        pauses: list[dict],
        output_path: str
) -> None:
    """
    Removes the specified pauses from an audio file, producing a shorter output.

    :param audio_file_path: Path to the source audio.
    :param pauses: A list of dicts, each with {"start": float, "end": float} in seconds,
                   indicating the regions to remove. They need not be sorted; we sort them.
    :param output_path: Where to save the trimmed audio.
    """
    # 1) Get the total duration of the audio
    total_duration = get_media_duration(audio_file_path)

    # 2) Sort pauses by start time (in case they're not already)
    sorted_pauses = sorted(pauses, key=lambda p: p["start"])

    # 3) Build a list of "keep intervals" (the segments outside the pauses)
    #    We'll go from 0 -> first_pause.start, then first_pause.end -> second_pause.start, etc.
    keep_intervals = []
    last_end = 0.0

    for pause in sorted_pauses:
        pause_start = pause["start"]
        pause_end = pause["end"]
        # If there's a non-empty interval before this pause, keep it
        if pause_start > last_end:
            keep_intervals.append((last_end, pause_start))
        last_end = max(last_end, pause_end)

    # Finally, if there's time after the last pause, keep it too
    if last_end < total_duration:
        keep_intervals.append((last_end, total_duration))

    # If there are no keep intervals, produce an empty 0-length audio (or handle differently)
    if not keep_intervals:
        raise ValueError("No intervals to keep. The output audio would be empty.")

    # 4) Build the filter_complex expression
    #
    # We create one atrim segment per keep interval, each labeled [sN],
    # then we concat them all into [outa].
    filter_segments = []
    for i, (start, end) in enumerate(keep_intervals):
        segment_label = f"[s{i}]"
        # Use asetpts to reset timestamps within each segment
        filter_segments.append(
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS{segment_label}"
        )

    # Then we reference them all in one concat filter
    concat_inputs = "".join(f"[s{i}]" for i in range(len(keep_intervals)))
    concat_command = f"{concat_inputs}concat=n={len(keep_intervals)}:v=0:a=1[outa]"

    # Combine all into a single filter_complex string
    filter_complex = ";".join(filter_segments + [concat_command])

    # 5) Construct and run the ffmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-hide_banner",
        "-loglevel", "warning",
        "-i", audio_file_path,
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        # Use any preferred audio codec and bitrate
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]

    print("Running FFmpeg command:")
    print(" ".join(shlex.quote(c) for c in cmd))

    subprocess.run(cmd, check=True)


def overlay_effect(video_path: str, effect_path: str, blend_mode: str, opacity: float, video_encoder: str,
                   output_path: str):
    """
    Apply an overlay effect to a video using a blend mode.

    :param video_encoder:
    :param opacity:
    :param video_path:  Path to the video file
    :param effect_path:  Path to the effect video file
    :param blend_mode:  The blend mode to use, e.g., "screen", "multiply", "overlay"
    :param output_path:  Path where to save the output video
    :return: None
    """
    try:
        cmd = [
            "ffmpeg", '-y',
            '-hide_banner',
            "-loglevel", "error",
            '-i', video_path,
            '-i', effect_path,
            '-filter_complex', f"[0:v][1:v]blend=all_mode='{blend_mode}':all_opacity={opacity}[outv]",
            '-map', '0:a?',
            '-map', '[outv]',
            '-c:a', 'copy',
            '-c:v', video_encoder,
            output_path
        ]

        print("Running ffmpeg:\n", " ".join(shlex.quote(arg) for arg in cmd))

        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg command failed with error: {e.stderr}")
