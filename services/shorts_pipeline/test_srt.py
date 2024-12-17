import unittest

class TestGenerateSrt(unittest.TestCase):
    def test_generate_srt_simple(self):
        # Example input
        text = "Hello world"
        # Characters: H   e   l   l   o       w   o   r   l   d
        # Indices:    0   1   2   3   4   5   6   7   8   9   10
        # ' ' at index 5
        characters = list(text)  # ['H','e','l','l','o',' ','w','o','r','l','d']
        # For simplicity, let's say each character starts at intervals of 0.1s
        # and ends 0.1s later.
        # "Hello" spans indices 0 to 4
        # " " at index 5
        # "world" spans indices 6 to 10
        character_start_times = [i * 0.1 for i in range(len(characters))]
        character_end_times = [(i * 0.1) + 0.1 for i in range(len(characters))]

        timestamps_dict = {
            'characters': characters,
            'character_start_times_seconds': character_start_times,
            'character_end_times_seconds': character_end_times
        }

        # Expected:
        # Subtitles per word:
        # 1: "Hello" from 0.00s to 0.5s (H at 0.0, e at 0.1, l at 0.2, l at 0.3, o at 0.4)
        # 2: "world" from 0.6s to 1.1s (w at 0.6, d ends at 1.1)
        #
        # SRT times are HH:MM:SS,mmm
        # 0.0s  -> "00:00:00,000"
        # 0.4s  -> "00:00:00,400" but end time should be from the last character of "Hello" which is 'o' at index=4
        #          start=0.0 end=0.5 (end char 'o' starts at 0.4 and ends at 0.5)
        #
        # For "world":
        # start at 'w' index=6: start=0.6s, ends with 'd' index=10: end=1.1s

        # Construct expected SRT:
        # Each subtitle block:
        # 1
        # 00:00:00,000 --> 00:00:00,500
        # Hello
        #
        # 2
        # 00:00:00,600 --> 00:00:01,100
        # world

        expected_srt = (
            "1\n00:00:00,000 --> 00:00:00,500\nHello\n\n"
            "2\n00:00:00,600 --> 00:00:01,100\nworld\n"
        )

        # Now test
        from io import StringIO

        # Import the function from its module if needed, for example:
        # from my_subtitle_module import generate_srt
        # For demonstration, I'll just redefine the function here quickly.

        def generate_srt(text, timestamps_dict):
            characters = timestamps_dict['characters']
            start_times = timestamps_dict['character_start_times_seconds']
            end_times = timestamps_dict['character_end_times_seconds']

            def format_time(seconds):
                ms = int((seconds - int(seconds)) * 1000)
                s = int(seconds)
                hrs = s // 3600
                mins = (s % 3600) // 60
                secs = s % 60
                return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

            words = text.split()
            srt_blocks = []
            char_index = 0

            for idx, word in enumerate(words, start=1):
                word_length = len(word)
                word_start_char_index = char_index
                word_end_char_index = word_start_char_index + word_length - 1

                actual_word_from_chars = ''.join(characters[word_start_char_index:word_end_char_index+1])
                if actual_word_from_chars != word:
                    raise ValueError(f"Word mismatch: expected '{word}', got '{actual_word_from_chars}'")

                word_start_time = start_times[word_start_char_index]
                word_end_time = end_times[word_end_char_index]

                start_str = format_time(word_start_time)
                end_str = format_time(word_end_time)

                srt_block = f"{idx}\n{start_str} --> {end_str}\n{word}\n"
                srt_blocks.append(srt_block)

                char_index += word_length
                # Advance past spaces
                while char_index < len(characters) and characters[char_index].isspace():
                    char_index += 1

            return "\n".join(srt_blocks)

        result = generate_srt(text, timestamps_dict)

        self.assertEqual(result, expected_srt)

if __name__ == "__main__":
    unittest.main()