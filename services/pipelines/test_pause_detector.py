import unittest

from services.pipelines.pause_detector import detect_pauses


class TestDetectPauses(unittest.TestCase):
    def test_detect_pauses_single(self):
        """
        In this scenario, there is exactly one large gap that exceeds the threshold
        and should be removed. Other gaps are smaller than threshold.
        """
        # Example words: sorted by start time
        #  - Gap between word0 end=0.5 and word1 start=1.2 => 0.7s (less than threshold=1.0)
        #  - Gap between word1 end=1.6 and word2 start=5.0 => 3.4s (exceeds threshold=1.0 => pause)
        words = [
            {"text": "Hello", "start": 0.0, "end": 0.5},
            {"text": "World", "start": 1.2, "end": 1.6},
            {"text": "!", "start": 5.0, "end": 5.1},
            {"text": "Goodbye", "start": 5.5, "end": 6.0},
        ]
        threshold = 1.0
        pad = 0.1

        # Import the function you want to test

        updated_words, pauses = detect_pauses(words=words, threshold=threshold, pad=pad)

        # Check that we found exactly one pause
        self.assertEqual(len(pauses), 1)
        # The detected pause should be from the end of "World" (1.6) to the start of "!"
        self.assertEqual(pauses[0], {"start": 1.7, "end": 4.9})

        # Check the updated timestamps
        #  3rd word ("!") should have been shifted backward by 3.4s
        expected_updated_words = [
            {"text": "Hello", "start": 0.0, "end": 0.5},
            {"text": "World", "start": 1.2, "end": 1.6},
            {"text": "!", "start": 1.8, "end": 1.9},
            {"text": "Goodbye", "start": 2.3, "end": 2.8},
        ]
        self.assertEqual(expected_updated_words, updated_words)

    def test_detect_pauses_none(self):
        """
        In this scenario, no gap exceeds the threshold, so no pauses should be removed.
        """
        from typing import List, Dict

        words = [
            {"text": "Alpha", "start": 0.0, "end": 0.5},
            {"text": "Beta", "start": 0.7, "end": 1.0},
            {"text": "Gamma", "start": 1.3, "end": 1.8},
        ]
        threshold = 1.0  # No gap > 1.0s here

        updated_words, pauses = detect_pauses(words, threshold)

        # No pauses detected
        self.assertEqual(pauses, [])
        # No shifts => updated words are unchanged
        self.assertEqual(updated_words, words)


if __name__ == "__main__":
    unittest.main()
