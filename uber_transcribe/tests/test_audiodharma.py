import unittest
from pathlib import Path
import tempfile
import shutil
import logging

from uber_transcribe.metadata_providers.audiodharma.provider import AudioDharmaProvider
from uber_transcribe.models import SourceItem, SourceType

logging.basicConfig(level=logging.INFO)

class TestAudioDharmaProviderIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir)
        self.provider = AudioDharmaProvider(cache_dir=self.cache_dir)

        html_path = Path(__file__).parent / "audiodharma-page1.html"
        with open(html_path, "r", encoding="utf-8") as f:
            self.html_content = f.read()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_scraping_and_cache_content(self):
        # This test checks the internal state of the provider after scraping,
        # which is an implementation detail, but it's useful for ensuring
        # the scraper is working as expected through the provider's public API.
        talks, speakers = self.provider.update_cache(html_content=self.html_content)

        # Assertions for talks (ported from scraper test)
        self.assertEqual(len(talks), 25)
        self.assertIn(24079, talks)
        talk = talks[24079]
        self.assertEqual(talk.title, "Stories & Buddhism: Sakka, The 5 Hindrances, and More")
        self.assertEqual(talk.date, "2025-10-26")
        self.assertEqual(talk.speaker_ids, [1])
        self.assertEqual(talk.youtube_id, "v9VUIR2cnpc")
        self.assertIsNotNone(talk.mp3_url)

        # Test a talk that has no video
        self.assertIn(24073, talks)
        talk_no_video = talks[24073]
        self.assertEqual(talk_no_video.title, "The Wealth of Enough")
        self.assertIsNone(talk_no_video.youtube_id)

        # Test a talk with a timestamp in the URL
        self.assertIn(24075, talks)
        talk_with_timestamp = talks[24075]
        self.assertEqual(talk_with_timestamp.start_time_seconds, 1898)

        # Test a talk with multiple speakers - the first one should be the one associated with the talk
        self.assertIn(24080, talks)
        talk_multi_speaker = talks[24080]
        self.assertEqual(talk_multi_speaker.speaker_ids, [241, 376])

        # Assertions for speakers (ported from scraper test)
        self.assertEqual(len(speakers), 7)
        self.assertIn(1, speakers)
        speaker = speakers[1]
        self.assertEqual(speaker.name, "Gil Fronsdal")
        self.assertEqual(speaker.url, "https://www.audiodharma.org/speakers/1")

        self.assertIn(241, speakers)
        self.assertEqual(speakers[241].name, "Dawn Neal")
        
        self.assertIn(376, speakers)
        self.assertEqual(speakers[376].name, "Kirsten Rudestam")

    def test_workflow(self):
        # 1. Test update_cache
        self.provider.update_cache(html_content=self.html_content)

        # Verify that cache files were created
        talks_path = self.cache_dir / "talks.json"
        speakers_path = self.cache_dir / "speakers.json"
        self.assertTrue(talks_path.exists())
        self.assertTrue(speakers_path.exists())

        # 2. Test get_all_source_items
        source_items = self.provider.get_all_source_items()
        self.assertGreater(len(source_items), 0)
        # Find a specific known youtube ID from the test file
        self.assertIn(
            "v9VUIR2cnpc", [item.source_id for item in source_items]
        )

        # 3. Test lookup
        test_item = SourceItem(
            source_id="v9VUIR2cnpc", source_type=SourceType.YOUTUBE_VIDEO
        )
        metadata = self.provider.lookup(test_item)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["speaker_names"], ["Gil Fronsdal"])
        self.assertEqual(len(metadata["audiodharma_talks"]), 1)
        self.assertEqual(
            metadata["audiodharma_talks"][0]["title"],
            "Stories & Buddhism: Sakka, The 5 Hindrances, and More",
        )
        self.assertEqual(
            metadata["audiodharma_urls"][0], "https://www.audiodharma.org/talks/24079"
        )


if __name__ == "__main__":
    unittest.main()
