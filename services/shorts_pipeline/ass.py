def generate_ass_with_highlights(data, output_file, words_per_line=5):
    grouped_lines = group_words_into_lines(data, words_per_line)

    with open(output_file, 'w') as f:
        # Header
        f.write("[Script Info]\n")
        f.write("Title: Highlighted RGB Subtitles\n")
        f.write("ScriptType: v4.00+\n")
        f.write("PlayResX: 1920\n")
        f.write("PlayResY: 1080\n\n")

        # Styles
        f.write("[V4+ Styles]\n")
        f.write(
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
        f.write(
            "Style: Default,Bebas Neue,72,&H00FFFFFF,&H00FF0000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,8,10,10,30,1\n\n")

        # Events
        f.write("[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

        highlight_colors = ["&H00FFFFFF"]

        for line_index, (words, line_start, line_end) in enumerate(grouped_lines):
            start_time = format_ass_timestamp(line_start)
            end_time = format_ass_timestamp(line_end)

            subtitle_text = ""
            for word_index, (word, word_start, word_end) in enumerate(words):
                highlight_color = highlight_colors[word_index % len(highlight_colors)]
                subtitle_text += (
                    f"{{\\1c{highlight_color}}}{word}{{\\1c&H00FFFFFF&}} "
                    if word_start == line_start or word_end == line_end
                    else
                    f"{word} "
                )

            subtitle_text = subtitle_text.strip()
            f.write(
                f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{{\\pos(960,720)\\fad(200,200)}}{subtitle_text}\n"
            )
def format_ass_timestamp(seconds):
    """Convert seconds to ASS timestamp format (hh:mm:ss.cc)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours:02}:{minutes:02}:{secs:02}.{centisecs:02}"


def group_words_into_lines(data, words_per_line=5):
    """Groups words into lines with start and end times."""
    grouped_lines = []
    current_line = []
    line_start_time = None
    line_end_time = None

    for i, (word, start, end) in enumerate(group_characters_into_words(data)):
        if not current_line:
            line_start_time = start
        current_line.append((word, start, end))
        line_end_time = end

        if len(current_line) >= words_per_line or i == len(data['characters']) - 1:
            grouped_lines.append((current_line, line_start_time, line_end_time))
            current_line = []

    return grouped_lines


def group_characters_into_words(data):
    words = []
    word = ""
    start_time = None
    end_time = None

    for i, char in enumerate(data['characters']):
        if char == " ":
            if word:
                words.append((word, start_time, end_time))
                word = ""
            continue

        if not word:
            start_time = data['character_start_times_seconds'][i]
        end_time = data['character_end_times_seconds'][i]
        word += char

    if word:
        words.append((word, start_time, end_time))

    return words