from typing import List, Dict, Any

def get_footage_segments(
    script_text: str,
    word_timings: List[Dict[str, float]],
    footages: List[str]
) -> Dict[str, Any]:
    """
    Given:
      - script_text: the original full script as one string (not strictly used except for reference).
      - word_timings: a list of dicts, each with:
          {
            "text": <word-string>,
            "start": <float-seconds>,
            "end":   <float-seconds>
          }
        representing the time range for each word in the script.
      - footages: a list of 5 file paths (strings) for the 'PLACE' segments, e.g.:
          ["place1.mp4", "place2.mp4", "place3.mp4", "place4.mp4", "place5.mp4"]

    Returns:
      A dictionary with:
        {
          "intro": {
            "start": float,
            "end": float
          },
          "segments": [
            {
              "footage": <footages[0]>,
              "start": float,
              "end": float
            },
            ...
            (five total entries, one per PLACE)
          ],
          "script_end": float
        }

    Explanation of fields:
      - "intro" covers t=0 up to the first PLACE's start.
      - Each entry in "segments" covers one PLACE interval, e.g. from the first
        PLACE's start time to the second PLACE's start time (and so forth).
      - "script_end" is the time of the final word in the script, which you
        might use to decide if you want the background to keep playing beyond
        the last PLACE or to trim the video.
    """

    # 1) Identify the times where "PLACE" occurs
    place_indices = []
    for i, wd in enumerate(word_timings):
        if wd["text"] == "PLACE":
            place_indices.append(i)

    if len(place_indices) != 5:
        raise ValueError("Expected exactly 5 occurrences of 'PLACE' in the script.")

    # 2) Determine the end of the script (time of the last word)
    script_end = word_timings[-1]["end"] if word_timings else 0.0

    # 3) Build the intro interval
    #    Intro from 0 up to the start time of the first "PLACE"
    first_place_start = word_timings[place_indices[0]]["start"]
    intro_segment = {
        "start": 0.0,
        "end": first_place_start
    }

    # 4) Build each "PLACE" segment
    #    segment i goes from place_i.start to place_(i+1).start (or script end)
    segments = []
    for idx in range(len(place_indices)):
        place_start = word_timings[place_indices[idx]]["start"]
        if idx < len(place_indices) - 1:
            # end at the next PLACE start
            place_end = word_timings[place_indices[idx + 1]]["start"]
        else:
            # last PLACE goes until the end of the script
            place_end = script_end

        segments.append({
            "footage": footages[idx],
            "start": place_start,
            "end": place_end
        })

    return {
        "intro": intro_segment,
        "segments": segments,
        "script_end": script_end
    }