import re
from typing import List, Dict

##############################################################################
# 2) Parse Script (with Inserted Footages)
##############################################################################

# We expect blocks like:
#   {{"video": "file_abc.mp4"}}
#   {{"photo": "file_logo.png"}}
# as well as plain text.

FOOTAGE_BLOCK_PATTERN = re.compile(
    r'\{\{\s*"(video|photo)"\s*:\s*"([^"]+)"\s*\}\}'
    # group(1) = "video" or "photo"
    # group(2) = "filename.ext"
)


def parse_script_with_footages(script: str) -> List[Dict]:
    """
    Splits the script into tokens: either 'footage' or 'text'.
    For a block like {{ "video": "file_abc.mp4" }}, we parse it into:
      {
        "type": "footage",
        "footage_kind": "video",
        "filename": "file_abc.mp4"
      }
    For plain text, we store:
      {
        "type": "text",
        "text": "some plain text..."
      }
    """
    tokens = []
    last_idx = 0

    for match in FOOTAGE_BLOCK_PATTERN.finditer(script):
        start, end = match.span()
        # text before this block
        if start > last_idx:
            chunk = script[last_idx:start].strip()
            if chunk:
                tokens.append({"type": "text", "text": chunk})
        footage_kind = match.group(1)  # "video" or "photo"
        filename = match.group(2)  # e.g. "file_abc.mp4"
        tokens.append({
            "type": "footage",
            "footage_kind": footage_kind,
            "filename": filename
        })
        last_idx = end

    # tail text
    if last_idx < len(script):
        tail_text = script[last_idx:].strip()
        if tail_text:
            tokens.append({"type": "text", "text": tail_text})

    return tokens


##############################################################################
# 3) Align Footages with Word Timestamps
##############################################################################

def assign_footage_timings(tokens: List[Dict], words: List[Dict], photo_length=1.0) -> List[Dict]:
    """
    Given 'tokens' from parse_script_with_footages(), and a 'words' array,
    produce a timed list of footages:
      [{"type": "video", "filename": "...", "start": 0.0, "end": 2.0}, ...]

    - Photo footages last a fixed length = photo_length
    - Video footages start at next word start,
      end at next footage's start or last word end if none left.
    - Re-use is already avoided by the GPT logic,
      but we won't re-check that here. If we see duplicates, we treat them as separate footages anyway.
    """
    word_idx = 0
    n_words = len(words)

    def get_next_word_start():
        nonlocal word_idx
        if word_idx >= n_words:
            return None
        return words[word_idx]["start"]

    # End of script = last word end
    script_end = words[-1]["end"] if n_words > 0 else 0.0

    timed_footages = []

    for i, token in enumerate(tokens):
        if token["type"] == "text":
            # Count how many words are in the text chunk, consume them from 'words'
            chunk_word_count = len(token["text"].split())
            word_idx += chunk_word_count

        elif token["type"] == "footage":
            kind = token["footage_kind"]  # "video" or "photo"
            filename = token["filename"]

            start_time = get_next_word_start()
            if start_time is None:
                start_time = script_end  # or 0 if no words

            if kind == "photo":
                end_time = start_time + photo_length
            else:  # video
                # find next footage token's start
                end_time = script_end
                for j in range(i + 1, len(tokens)):
                    if tokens[j]["type"] == "footage":
                        # We temporarily move word_idx forward to consume text between i+1..j
                        old_idx = word_idx
                        for k in range(i + 1, j):
                            if tokens[k]["type"] == "text":
                                c = len(tokens[k]["text"].split())
                                word_idx += c
                        next_start = get_next_word_start()
                        word_idx = old_idx
                        if next_start is not None:
                            end_time = next_start
                        break

            timed_footages.append({
                "type": kind,
                "filename": filename,
                "start": start_time,
                "end": end_time
            })

    return timed_footages


##############################################################################
# 4) Top-Level Function
##############################################################################

def parse_and_time_script(script: str, words: List[Dict], photo_length=1.0) -> List[Dict]:
    """
    1) Parse script for footages
    2) Align them with words
    3) Return timed footages
    """
    tokens = parse_script_with_footages(script)
    timed_footages = assign_footage_timings(tokens, words, photo_length=photo_length)
    return timed_footages
