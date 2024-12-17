def build_concat_cmd(input_file_paths: list[str], output_file_path: str) -> list[str]:
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
        "-c:v", "libx264",
        "-crf", "23",
        "-y",  # Overwrite output if it exists
        output_file_path
    ])

    # Join into a single command string
    return command
