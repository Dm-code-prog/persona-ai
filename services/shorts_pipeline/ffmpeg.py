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
