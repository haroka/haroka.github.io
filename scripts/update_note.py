#!/usr/bin/env python3
"""Fetch validated public note RSS and update only the generated article block."""
import argparse
import html
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from datetime import timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
FEED = 'https://note.com/haroppe/rss'
START = '<!-- NOTE-LATEST:START -->'
END = '<!-- NOTE-LATEST:END -->'
MAX_BYTES = 2_000_000


def parse_feed(raw):
    if len(raw) > MAX_BYTES or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Unsupported RSS document')
    root = ET.fromstring(raw)
    if root.tag != 'rss' or root.find('channel') is None:
        raise ValueError('Expected RSS channel')
    articles = {}
    for item in root.findall('./channel/item'):
        url = (item.findtext('link') or '').strip()
        if not re.fullmatch(r'https://note\.com/haroppe/n/n[0-9a-f]+', url):
            raise ValueError('Unexpected article URL')
        title = (item.findtext('title') or '').strip()
        if not title or len(title) > 500:
            raise ValueError('Missing or excessive title')
        dt = parsedate_to_datetime(item.findtext('pubDate') or '')
        if dt.tzinfo is None:
            raise ValueError('Publication date needs timezone')
        thumb = item.find('{http://search.yahoo.com/mrss/}thumbnail')
        image = '' if thumb is None else (thumb.get('url') or thumb.text or '').strip()
        parsed = urlsplit(image)
        if image and (parsed.scheme != 'https' or parsed.hostname not in {'assets.st-note.com', 'images.st-note.com', 'd2l930y2yx77uc.cloudfront.net'} or parsed.username or parsed.password or parsed.port not in {None, 443}):
            image = ''
        articles[url] = {'title': title, 'url': url, 'published': dt.astimezone(timezone.utc).isoformat(), 'date': dt.strftime('%Y.%m.%d'), 'image': image}
    if not articles:
        raise ValueError('Empty RSS; preserving previous successful data')
    return sorted(articles.values(), key=lambda a: a['published'], reverse=True)[:6]


def render(articles):
    cards = []
    for a in articles:
        esc = lambda s: html.escape(s, quote=True)
        image = f'<img class="article-thumb" src="{esc(a["image"])}" alt="" loading="lazy">' if a['image'] else ''
        cards.append(f'''      <a class="article-card" href="{esc(a['url'])}" target="_blank" rel="noopener noreferrer">
        {image}
        <div class="article-body">
          <div class="article-meta"><span class="article-tag">note</span><span class="article-date">{esc(a['date'])}</span></div>
          <div class="article-title">{esc(a['title'])}</div>
          <div class="article-footer"><span class="article-venue">note</span><span class="article-arrow">→</span></div>
        </div>
      </a>''')
    return '\n    <div class="cat-divider fade-up"><span class="cat-label">最近のnote</span></div>\n    <div class="articles-grid fade-up">\n' + '\n'.join(cards) + '\n    </div>\n    '


def replace_block(page, articles):
    if page.count(START) != 1 or page.count(END) != 1:
        raise ValueError('Exactly one generated block is required')
    before, rest = page.split(START)
    _, after = rest.split(END)
    return before + START + render(articles) + END + after


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
        f.write(text)
        temp = Path(f.name)
    os.replace(temp, path)


def update(root, raw):
    articles = parse_feed(raw)
    page_path = root / 'index.html'
    page = page_path.read_text(encoding='utf-8')
    updated = replace_block(page, articles)
    data = json.dumps(articles, ensure_ascii=False, indent=2) + '\n'
    changed = False
    for path, text in [(page_path, updated), (root / 'assets/note-latest.json', data)]:
        if not path.exists() or path.read_text(encoding='utf-8') != text:
            atomic_write(path, text)
            changed = True
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--feed-file', type=Path)
    parser.add_argument('--allow-stale', action='store_true')
    args = parser.parse_args()
    try:
        if args.feed_file:
            raw = args.feed_file.read_bytes()
        else:
            with urlopen(Request(FEED, headers={'User-Agent': 'haroka-site-note-sync/1.0'}), timeout=30) as response:
                if response.url != FEED:
                    raise ValueError('Unexpected feed redirect')
                raw = response.read(MAX_BYTES + 1)
        print('Updated note articles' if update(ROOT, raw) else 'No changes')
    except Exception as exc:
        print(f'RSS update failed; previous data kept: {exc}', file=sys.stderr)
        cache = ROOT / 'assets/note-latest.json'
        if args.allow_stale and cache.exists():
            saved = json.loads(cache.read_text(encoding='utf-8'))
            page = (ROOT / 'index.html').read_text(encoding='utf-8')
            if saved and replace_block(page, saved) == page:
                return
        raise SystemExit(1)


if __name__ == '__main__':
    main()
