import importlib.util
from pathlib import Path
import tempfile
import unittest

s = importlib.util.spec_from_file_location('sync', Path(__file__).resolve().parents[1] / 'scripts/update_note.py')
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)


def feed(title='Safe &amp; title', url='https://note.com/haroppe/n/n012abc', image='https://assets.st-note.com/img.png'):
    return f'<rss xmlns:media="http://search.yahoo.com/mrss/"><channel><item><title>{title}</title><link>{url}</link><pubDate>Wed, 07 Oct 2026 18:13:45 +0900</pubDate><media:thumbnail>{image}</media:thumbnail></item></channel></rss>'.encode()


class FeedTests(unittest.TestCase):
    def test_title_escaped_and_thumbnail_allowlist(self):
        result = m.render(m.parse_feed(feed('&lt;script&gt;alert(1)&lt;/script&gt;', image='https://evil.example/a')))
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)
        self.assertNotIn('evil.example', result)

    def test_reject_foreign_article_and_empty_feed(self):
        for raw in [feed(url='https://note.com/other/n/n012abc'), b'<rss><channel/></rss>', b'not xml']:
            with self.assertRaises(Exception):
                m.parse_feed(raw)

    def test_unchanged_and_failed_updates_preserve_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'index.html').write_text('curated talks' + m.START + m.END + 'curated series')
            self.assertTrue(m.update(root, feed()))
            page = (root / 'index.html').read_bytes()
            data = (root / 'assets/note-latest.json').read_bytes()
            self.assertFalse(m.update(root, feed()))
            with self.assertRaises(Exception):
                m.update(root, b'<rss><channel/></rss>')
            self.assertEqual(page, (root / 'index.html').read_bytes())
            self.assertEqual(data, (root / 'assets/note-latest.json').read_bytes())
            self.assertTrue(page.startswith(b'curated talks'))
            self.assertTrue(page.endswith(b'curated series'))

    def test_duplicate_markers_fail_before_writes(self):
        with self.assertRaises(ValueError):
            m.replace_block(m.START + m.START + m.END, m.parse_feed(feed()))

    def test_date_normalized(self):
        self.assertEqual(m.parse_feed(feed())[0]['published'], '2026-10-07T09:13:45+00:00')
