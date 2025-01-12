import subprocess
import shlex

def overlay_videos(background_footage_path, footages, output_path, video_encoder):
    """
    Creates a final video where 'background_footage_path' is the base,
    and each item in 'footages' is overlaid in a specified time window.

    All the footages and the background video must be correctly formatted
    before calling this function. The final video will be saved at 'output_path'.

    :param background_footage_path: str, path to the background video (the final length).
    :param footages: list of dicts, each like:
                     {
                       "footage": "path/to/overlayN.mp4",
                       "start": float,  # e.g., 4.0
                       "end": float     # e.g., 12.0
                     }
    :param output_path: str, path to save the final video.
    :param video_encoder: e.g. "h264_videotoolbox" (macOS) or "libx264"
    """
    # 1) Build the base ffmpeg command, adding the background as the first input
    cmd = [
        "ffmpeg",
        "-y",                 # overwrite output if it exists
        "-hide_banner",
        "-loglevel", "warning",
        "-i", background_footage_path  # input #0 => background
    ]

    # 2) Add each overlay footage as a separate input
    for item in footages:
        cmd += ["-i", item["footage"]]  # input #1..N => overlays

    # 3) Construct the filter_complex
    #    We'll chain overlays in sequence on top of the background.
    filter_parts = []
    current_label = "[0:v]"  # background is [0:v]

    # Each overlay is at input index i (1-based for the overlays), so [i:v]
    # We'll:
    #   - setpts=PTS-STARTPTS + start/TB => [ov{i}]
    #   - overlay => [v{i}]
    # Then move on with [v{i}] as the new "base" for the next overlay.
    for i, item in enumerate(footages, start=1):
        start = item["start"]
        end   = item["end"]
        ov_label  = f"[ov{i}]"
        out_label = f"[v{i}]"

        # Step A: reset & offset PTS so the overlay effectively starts at 'start' seconds
        # e.g. [1:v]setpts=PTS-STARTPTS+4/TB[ov1]
        filter_parts.append(
            f"[{i}:v]setpts=PTS-STARTPTS+{start}/TB{ov_label}"
        )

        # Step B: overlay it onto the current_label between 'start' and 'end'
        # e.g. [0:v][ov1]overlay=enable='between(t,4,12)'[v1]
        filter_parts.append(
            f"{current_label}{ov_label}overlay=enable='between(t,{start},{end})'{out_label}"
        )

        # Now the result of this overlay is the new base for the next iteration
        current_label = out_label

    # Join all filter steps with semicolons
    filter_complex = "; ".join(filter_parts)

    # 4) Finish constructing the ffmpeg command
    cmd += [
        # Provide the filtergraph
        "-filter_complex", filter_complex,
        # Map the final labeled output to the output file
        "-map", current_label,
        # Use the desired encoder
        "-c:v", video_encoder,
        # Drop audio (or change to -c:a copy, amix, etc., if needed)
        "-an",
        output_path
    ]

    # 5) (Optional) Print the command for debugging
    print("Running ffmpeg:\n", " ".join(shlex.quote(c) for c in cmd))

    # 6) Execute the ffmpeg process
    subprocess.run(cmd, check=True)

    print(f"Done! Final video at: {output_path}")