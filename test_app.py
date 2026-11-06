import unittest

import app


class ChunkTextTests(unittest.TestCase):
    def test_splits_long_text_without_losing_words(self):
        text = " ".join(f"woord{index}" for index in range(100))
        chunks = app.chunk_text(text, limit=80)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 80 for chunk in chunks))
        self.assertEqual(" ".join(chunks), text)

    def test_keeps_short_paragraphs_together_and_skips_empty_lines(self):
        chunks = app.chunk_text("Eerste alinea.\n\nTweede alinea.", limit=40)

        self.assertEqual(chunks, ["Eerste alinea.\nTweede alinea."])

    def test_splits_a_long_paragraph_at_word_boundaries(self):
        chunks = app.chunk_text("abcdefghij klmnopqrst uvwxyz", limit=12)

        self.assertEqual(chunks, ["abcdefghij", "klmnopqrst", "uvwxyz"])


class SummaryInstructionTests(unittest.TestCase):
    def test_supported_styles_have_distinct_instructions(self):
        meeting = app._summary_instructions("meeting")
        session = app._summary_instructions("session")
        general = app._summary_instructions("general")

        self.assertIn("actiepunten", meeting)
        self.assertIn("geen diagnose", session)
        self.assertIn("korte", general)


class WhisperProgressTests(unittest.TestCase):
    def test_parses_live_whisper_segment_with_hours(self):
        segment = app._parse_whisper_segment(
            "[01:02:03.456 --> 01:02:04.123] Hallo daar"
        )

        self.assertEqual(segment, (3723.456, 3724.123, "Hallo daar"))

    def test_ignores_non_segment_output(self):
        self.assertIsNone(app._parse_whisper_segment("Detected language: Dutch"))


if __name__ == "__main__":
    unittest.main()
