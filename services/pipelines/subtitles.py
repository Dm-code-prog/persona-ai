import moviepy as mp
from moviepy import TextClip
import moviepy.video.fx as vfx


def group_chars_into_words(chars, starts, ends):
    """
    Groups character-level data into words based on spaces/newlines.
    Returns a list of dicts like:
      [
        { "text": "Do", "start": 0.0, "end": 0.197 },
        { "text": "you", "start": 0.197, "end": 0.279 },
        ...
      ]
    """
    words = []
    current_word_chars = []
    current_word_start = None
    current_word_end = None

    for i, ch in enumerate(chars):
        # If this looks like whitespace or newline, that means we close the word if we have one
        if ch.isspace():
            if current_word_chars:
                # We have a completed word
                words.append({
                    "text": "".join(current_word_chars),
                    "start": current_word_start,
                    "end": current_word_end
                })
                current_word_chars = []
                current_word_start = None
                current_word_end = None
        else:
            # Start building (or continue building) a word
            if not current_word_chars:
                # New word starts
                current_word_start = starts[i]
            current_word_chars.append(ch)
            current_word_end = ends[i]

    # If we ended the loop but still have an unfinished word
    if current_word_chars:
        words.append({
            "text": "".join(current_word_chars),
            "start": current_word_start,
            "end": current_word_end
        })

    return words


import re


def group_words_into_sentences(words, max_words_in_sentence=3):
    """
    Splits the word list into sentences whenever we see a period, question mark, or exclamation mark
    at the end of a word (like "goals?" or "cake.") or when the maximum word count is reached.

    Parameters:
        words (list): List of word dictionaries.
        max_words_in_sentence (int): Maximum number of words per sentence.

    Returns:
        list: List of sentences, each a list of word dicts.
    """
    sentences = []
    current_sentence = []

    for w in words:
        current_sentence.append(w)

        # Check if the word ends with punctuation indicating a sentence boundary
        if re.search(r'[.?!]\Z', w["text"]) or len(current_sentence) >= max_words_in_sentence:
            # End current sentence
            sentences.append(current_sentence)
            current_sentence = []

    # Add any remaining words as the last sentence
    if current_sentence:
        sentences.append(current_sentence)

    return sentences


def measure_text_width(text, font, fontsize):
    """
    Returns the (width, height) of the rendered text
    by creating a temporary TextClip and reading .size
    """
    temp_clip = mp.TextClip(
        text=text,
        font=font,
        font_size=fontsize,
        color='white'
    )
    return temp_clip.size  # (w, h)


def create_line_with_word_highlight(
        word_data,
        video_w=1080,
        video_h=1920,
        font='BebasNeue-Regular',
        fontsize=60,
        base_color='white',
        highlight_bg='#A020F0BB',
        line_y_ratio=0.8
) -> list[TextClip]:
    """
    Returns a CompositeVideoClip that:
    1. Displays line_text in `base_color` from line_start->line_end
    2. For each word in word_data, overlays a highlight background
       from word.start->word.end, behind the word.

    - line_y_ratio: 0.8 => place the line at 80% down the screen
    - highlight_bg: a partially transparent purple, e.g. #A020F0BB
    """

    # (A) Create the baseline in white (or base_color).

    line_text = " ".join(w["text"] for w in word_data)

    line_start = word_data[0]["start"]
    line_end = word_data[-1]["end"]

    base_line = mp.TextClip(
        text=line_text,
        font=font,
        font_size=fontsize,
        color=base_color,
        margin=(12, 12)
    )

    line_w, line_h = base_line.size
    # Position in the bottom center (for example):
    x_center = (video_w - line_w) / 2
    y_pos = video_h * line_y_ratio

    base_line = (base_line
                 .with_start(line_start)
                 .with_duration(line_end - line_start)
                 .with_position((x_center, y_pos))
                 )

    highlight_clips = []

    words_list = line_text.split()

    partial_texts = []
    for i in range(len(words_list)):
        partial_texts.append(" ".join(words_list[:i]) + (" " if i > 0 else ""))

    # Pre-measure all partial_text widths
    offsets = []
    for p in partial_texts:
        w_size, _ = measure_text_width(p, font, fontsize)
        offsets.append(w_size)

    for i, w in enumerate(word_data):
        w_text = w["text"]
        w_start = w["start"]
        w_end = w["end"]

        w_x = x_center + offsets[i]
        w_y = y_pos

        width, height = measure_text_width(w_text, font, fontsize)

        highlight_clip: mp.TextClip = mp.TextClip(
            text=w_text,
            font=font,
            font_size=fontsize,
            color='white',  # text color
            bg_color=highlight_bg,  # partial purple background
            method='caption',
            size=(width, height),
            transparent=True,
            margin=(12, 12)
        )

        # Reposition & timing
        highlight_clip = (
            highlight_clip
            .with_position((w_x, w_y))
            .with_start(w_start)
            .with_end(w_end)
            .with_duration(w_end - w_start)
            .with_effects([vfx.Blink(duration_on=0.5, duration_off=0.5)])
        )

        highlight_clips.append(highlight_clip)

    return [base_line, *highlight_clips]


def add_subtitles(video_path: str, sentences: list, video_duration: float, output_path: str,
                  highlight_color: str = '#7710e2', color='white'):
    """
    Add subtitles to a video file.
    :param color:
    :param highlight_color:
    :param output_path:  Path where to save the output video.
    :param video_duration:  Duration of the video in seconds.
    :param video_path:  Path to the video file.
    :param sentences:  List of sentences, each a list of word dicts.
    :return: None
    """

    text_clips: list[TextClip] = []

    video_clip = mp.VideoFileClip(
        filename=video_path,
        audio=True,
    )

    for s in sentences:
        clip = create_line_with_word_highlight(
            s,
            video_w=1080,
            video_h=1920,
            font='BebasNeue-Regular',
            fontsize=100,
            base_color=color,
            highlight_bg=highlight_color,
            line_y_ratio=0.8
        )
        text_clips.extend(clip)

    video = mp.CompositeVideoClip([video_clip] + text_clips).with_duration(video_duration)
    video.write_videofile(
        output_path,
        codec="libx264",
        fps=30,
        audio=True,
        audio_codec='aac',
        preset='ultrafast',
        threads=4,
        audio_bitrate='320k',
    )
