"""Short film introductions from identified work pages and saved article sections."""
import json
import re
import unicodedata

SYNOPSIS_LIMIT = 480
INTRO_SECTIONS = {'eiga-com': '解説・あらすじ', 'bfi-lff': 'Introduction'}
STREAM_NOTICE = re.compile(r'^[^。]{2,70}(?:から配信|より配信|に配信開始)[。．]\s*')
ARTICLE_ID = re.compile(r'live-[a-f0-9]{24}')


def prose(value, language, url):
    text = ' '.join(value.split()) if isinstance(value, str) else ''
    if language == 'ja':
        text = STREAM_NOTICE.sub('', text, count=1)
    if len(text) < 20:
        return {}
    if len(text) > SYNOPSIS_LIMIT:
        prefix = text[:SYNOPSIS_LIMIT]
        finish = max(prefix.rfind(mark) for mark in ('。', '！', '？', '. ', '! ', '? '))
        text = prefix[:finish+1] if finish >= SYNOPSIS_LIMIT // 2 else prefix.rstrip() + '…'
    return {'text': text, 'language': language, 'source_url': url}


def _blocks(value):
    try:
        blocks = json.loads(value or '[]')
    except (TypeError, ValueError):
        return []
    return blocks if isinstance(blocks, list) and all(isinstance(block, dict) for block in blocks) else []


def article_profiles(articles, event_sources):
    """Reuse the prose after the publisher's synopsis heading in the matching article."""
    profiles = {}
    for row in articles:
        url = row.get('canonical_url')
        identifier = row.get('id') or ''
        section = INTRO_SECTIONS.get(row.get('source_id'))
        if not section or row.get('is_demo') or url not in event_sources.get(identifier, ()) or not ARTICLE_ID.fullmatch(identifier):
            continue
        original = _blocks(row.get('article_blocks_json'))
        start = next((i for i, block in enumerate(original) if block.get('type') == 'heading' and block.get('text') == section), None)
        if start is None:
            continue
        index = None
        for i in range(start + 1, len(original)):
            if original[i].get('type') == 'heading':
                break
            if original[i].get('type') == 'paragraph' and len(original[i].get('text') or '') >= 40:
                index = i
                break
        if index is None:
            continue
        translated = _blocks(row.get('editorial_blocks_json')) if row.get('editorial_status') in ('translated', 'reviewed') else []
        if len(translated) == len(original) and all(a.get('type') == b.get('type') for a, b in zip(original, translated)):
            profile = prose(translated[index].get('text'), 'zh-CN', url)
        else:
            profile = {}
        profile = profile or prose(original[index].get('text'), row.get('language') or 'und', url)
        if profile:
            profiles[url] = {**profile, 'article_id': identifier}
    return profiles


def eiga_profile(soup, url):
    section = next((heading.parent for heading in soup.select('.txt-block > h2')
                    if heading.get_text(strip=True) == '解説・あらすじ'), None)
    paragraphs = section.find_all('p', recursive=False) if section else []
    text = ' '.join(node.get_text(' ', strip=True) for node in paragraphs if 'data' not in (node.get('class') or []))
    profile = prose(text, 'ja', url)
    data = soup.select_one('p.data')
    credits = unicodedata.normalize('NFKC', data.get_text(' ', strip=True)) if data else ''
    if year := re.search(r'\b(18\d{2}|19\d{2}|20\d{2})年製作', credits):
        profile['year'] = int(year[1])
    if runtime := re.search(r'(?:^|[／/])\s*(\d{1,3})\s*分(?=[／/\s]|$)', credits):
        profile['runtime_minutes'] = int(runtime[1])
    for label in soup.select('dl.movie-staff dt'):
        if label.get_text(strip=True) != '監督':
            continue
        names = []
        for credit in label.find_next_siblings():
            if credit.name != 'dd':
                break
            name = credit.get_text(' ', strip=True)
            if name:
                names.append(name)
        if names:
            profile['directors'] = list(dict.fromkeys(names))[:6]
        break
    return profile
