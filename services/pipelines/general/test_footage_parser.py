import pytest
from footage_parser import (
    parse_script_with_footages,
    parse_and_time_script
)

def test_parse_script_with_footages():
    script = """Here is some text
                {{"video": "file_abc.mp4"}}
                More text
                {{"photo": "file_logo.png"}}
                The end."""
    tokens = parse_script_with_footages(script)
    assert len(tokens) == 5
    assert tokens[0]["type"] == "text"
    assert tokens[1]["type"] == "footage"
    assert tokens[1]["footage_kind"] == "video"
    assert tokens[1]["filename"] == "file_abc.mp4"
    assert tokens[3]["footage_kind"] == "photo"

def test_parse_and_time_script():
    script = """Hello world
                {{"video": "file_abc.mp4"}}
                This is a test
                {{"photo": "file_logo.png"}}
                done"""
    words = [
        {"text": "Hello", "start": 0.0, "end": 0.5},
        {"text": "world", "start": 0.5, "end": 1.0},
        {"text": "This", "start": 1.0, "end": 1.2},
        {"text": "is", "start": 1.2, "end": 1.4},
        {"text": "a", "start": 1.4, "end": 1.5},
        {"text": "test", "start": 1.5, "end": 2.0},
        {"text": "done", "start": 2.0, "end": 2.5},
    ]
    timed = parse_and_time_script(script, words, photo_length=1.0)
    # We should get 2 footages
    assert len(timed) == 2
    # First footage is video
    assert timed[0]["type"] == "video"
    assert timed[0]["filename"] == "file_abc.mp4"
    # starts at next word start => 1.0, ends at next footage => 2.0
    assert pytest.approx(timed[0]["start"], 0.01) == 1.0
    assert pytest.approx(timed[0]["end"], 0.01) == 2.0
    # second is photo
    assert timed[1]["type"] == "photo"
    assert timed[1]["filename"] == "file_logo.png"
    # starts at next word => 2.0, ends => 2.0+1.0=3.0
    assert pytest.approx(timed[1]["start"], 0.01) == 2.0
    assert pytest.approx(timed[1]["end"], 0.01) == 3.0