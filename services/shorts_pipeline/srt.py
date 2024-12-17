def generate_srt(text, timestamps_dict):
    """
    Generate SRT subtitles from ElevenLabs character-level timestamps.

    :param text: The original text string used to generate the audio.
    :param timestamps_dict: A dictionary with keys:
        - 'characters': list of characters corresponding to the text
        - 'character_start_times_seconds': list of start times per character
        - 'character_end_times_seconds': list of end times per character
    :return: A string containing SRT subtitles.
    """

    characters = timestamps_dict['characters']
    start_times = timestamps_dict['character_start_times_seconds']
    end_times = timestamps_dict['character_end_times_seconds']

    # Helper to format seconds into SRT time format "HH:MM:SS,mmm"
    def format_time(seconds) -> str:
        ms = int((seconds - int(seconds)) * 1000)
        s = int(seconds)
        hrs = s // 3600
        mins = (s % 3600) // 60
        secs = s % 60
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

    # Split text into words by whitespace
    words = text.split()

    # We'll iterate through characters and match them to words
    srt_blocks = []
    char_index = 0

    for idx, word in enumerate(words, start=1):
        # Accumulate characters for this word
        word_length = len(word)
        word_start_char_index = char_index
        word_end_char_index = word_start_char_index + word_length - 1

        # word_characters: the subset of characters for this word
        # Since we have a 1-to-1 mapping, we can directly slice
        # But we should verify that the sliced characters match `word`
        actual_word_from_chars = ''.join(characters[word_start_char_index:word_end_char_index + 1])
        if actual_word_from_chars != word:
            # If they don't match, there's a discrepancy (e.g., multiple spaces, punctuation differences)
            # A more robust approach might be needed. For now, we assume it matches.
            raise ValueError(f"Word mismatch: expected '{word}', got '{actual_word_from_chars}'")

        # Determine timing for this word
        word_start_time = start_times[word_start_char_index]
        word_end_time = end_times[word_end_char_index]

        start_str = format_time(word_start_time)
        end_str = format_time(word_end_time)

        # Create SRT block
        srt_block = f"{idx}\n{start_str} --> {end_str}\n{word}\n"
        srt_blocks.append(srt_block)

        # Move character index forward
        char_index += word_length
        # Skip over any trailing spaces in the characters array
        # Since `text.split()` removes spaces, we need to advance char_index for spaces in characters
        # until we hit the start of the next word.
        while char_index < len(characters) and characters[char_index].isspace():
            char_index += 1

    # Join all subtitle blocks with a blank line between them
    srt_output = "\n".join(srt_blocks)
    return srt_output

# Example usage (pseudo-code):
# text = "Hello! 你好! Hola!"
# timestamps_dict = {
#     'characters': ['H', 'e', 'l', 'l', 'o', '!', ' ', '你', '好', '!', ' ', 'H', 'o', 'l', 'a', '!'],
#     'character_start_times_seconds': [...],
#     'character_end_times_seconds': [...]
# }
# srt_content = generate_srt(text, timestamps_dict)
# print(srt_content)