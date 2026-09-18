import unittest

from app.diarizer import speaker_blocks


class SpeakerBlockTests(unittest.TestCase):
    def test_same_speaker_is_merged(self):
        turns = [
            {"start_seconds": 10.0, "end_seconds": 20.0, "speaker": "SPEAKER_00"},
            {"start_seconds": 22.0, "end_seconds": 35.0, "speaker": "SPEAKER_00"},
            {"start_seconds": 40.0, "end_seconds": 55.0, "speaker": "SPEAKER_01"},
        ]
        result = speaker_blocks(
            turns,
            min_turn_duration=8.0,
            merge_same_speaker_gap=4.0,
            padding=1.0,
            total_duration=60.0,
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["speaker"], "SPEAKER_00")
        self.assertEqual(result[0]["start_seconds"], 9.0)
        self.assertEqual(result[0]["end_seconds"], 36.0)


if __name__ == "__main__":
    unittest.main()
