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
            (root / 'index.html').write_text('curated talks' + m.START + m.END + '<!-- NOTE-AI:START --><!-- NOTE-AI:END -->' + 'curated series')
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


class AISelectionTests(unittest.TestCase):
    def article(self, title, key, published='2026-10-01T00:00:00+00:00'):
        return {'title': title, 'url': 'https://note.com/haroppe/n/n' + key, 'published': published, 'date': '2026.10.01', 'image': ''}

    def test_confirmed_dots_and_exclusions(self):
        dots = self.article('dotsを使って一週間', 'a1')
        pair = self.article('ペアカードなしで暮らせなくなるまで', 'a2')
        poster = self.article('ポスターセッション一気見', 'a3')
        ai = self.article('AIエージェントの静かな劣化', 'a4')
        config = {'include_urls': [dots['url']], 'exclude_urls': [pair['url'], poster['url']]}
        result = m.select_ai([dots, pair, poster, ai], [], config)
        self.assertEqual({a['url'] for a in result}, {dots['url'], ai['url']})

    def test_skill_and_claude_terms(self):
        items = [self.article('Skill、先祖返りしてない？descriptionで防ぐ', 'b1'), self.article('Claude Meetupで登壇', 'b2'), self.article('DAILYの仕事', 'b3')]
        self.assertEqual(len(m.select_ai(items, [], {})), 2)

    def test_ai_selection_uses_feed_beyond_latest_six_and_deduplicates(self):
        import xml.etree.ElementTree as ET
        rss = ET.Element('rss')
        channel = ET.SubElement(rss, 'channel')
        for i in range(7):
            one = ET.fromstring(feed(title='AIの記事' if i == 6 else '非技術の話', url='https://note.com/haroppe/n/n' + str(i)))
            channel.append(one.find('./channel/item'))
        articles = m.parse_feed(ET.tostring(rss))
        self.assertEqual(len(articles), 7)
        ai = m.select_ai(articles, [articles[6]], {})
        self.assertEqual(len(ai), 1)
        self.assertEqual(ai[0]['url'], articles[6]['url'])

    def test_previous_success_is_kept_when_no_new_ai_article(self):
        old = self.article('以前のAI実践', 'c1')
        self.assertEqual(m.select_ai([self.article('ペアカード', 'c2')], [old], {}), [old])

    def test_fetch_failure_preserves_both_blocks(self):
        import json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'index.html').write_text(m.START + m.END + '<!-- NOTE-AI:START --><!-- NOTE-AI:END -->')
            m.update(root, feed(title='AIの記事'))
            before = {p.name: p.read_bytes() for p in [root / 'index.html', root / 'assets/note-latest.json', root / 'assets/note-ai.json']}
            with patch.object(m, 'ROOT', root), patch.object(m, 'urlopen', side_effect=OSError('offline')), patch('sys.argv', ['sync', '--allow-stale']):
                m.main()
            after = {p.name: p.read_bytes() for p in [root / 'index.html', root / 'assets/note-latest.json', root / 'assets/note-ai.json']}
            self.assertEqual(before, after)
