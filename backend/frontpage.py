"""Mirror CultureCore.frontpageRows for the public edition, without changing layout."""
import json
import math
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
EDITORIAL_POINTS = {'major': 56, 'outcome': 46, 'programme': 30, 'reporting': 22, 'ordinary': 16, 'service': 6}
EVENTS = (
    ('art', 'venice', r'venice(?:[ -]+(?:art|architecture))?[ -]+biennal[ei]|venedig[ -]+biennale|biennale (?:arte|di venezia)|威尼斯(?:艺术|藝術|建筑|建築)?[双雙]年展|(?:ヴェネ(?:チ|ツィ)ア|ベネチア)[・\s]*ビエンナーレ'),
    ('art', 'whitney', r'whitney biennial|惠特尼[双雙]年展|ホイットニー.{0,3}ビエンナーレ'),
    ('art', 'documenta', r'\bdocumenta\b|卡塞尔文献展|ドクメンタ'),
    ('film', 'cannes', r'\bcannes\b|戛纳|カンヌ'),
    ('film', 'berlinale', r'berlinale|berlin.{0,20}film festival|柏林[国國]际电影节|ベルリン国際映画祭'),
    ('film', 'oscars', r'\boscars?\b|academy awards?|奥斯卡|アカデミー賞'),
    ('photography', 'photobook-awards', r'photobook awards?|写真集賞'),
    ('photography', 'prix-pictet', r'prix pictet|ピクテ賞'),
    ('photography', 'hasselblad', r'hasselblad award|ハッセルブラッド国際写真賞'),
)
EVENTS = tuple((desk, key, re.compile(pattern)) for desk, key, pattern in EVENTS)
RESULT = re.compile(
    r'\b(?:wins?|won|takes?|receives?|honou?red|awarded)\b.{0,70}\b(?:awards?|prizes?|lions?|oscars?)\b'
    r'|\b(?:awards?|prizes?|lions?|oscars?)\b.{0,60}\b(?:announced|go(?:es)? to|awarded)\b'
    r'|\b(?:awards?|prizes?) winners(?:\s*(?:[:—|]|$)|\s+(?:list|announced|revealed))'
    r'|dévoile son palmarès|palmarès.{0,15}(?:annoncé|révélé)|(?:publica|anuncia|revela).{0,30}(?:ganadores|vencedores|premiados)'
    r'|获奖名单|[頒颁]奖结果|宣布.{0,15}获奖|発表.{0,18}(?:受賞者|受賞作)|(?:受賞者|受賞作).{0,18}発表|最優秀賞を受賞'
)
APPOINTMENT = re.compile(
    r'\b(?:appoint\w*|name[ds]|tapped|chosen)\b.{0,30}\b(?:curat\w*|artistic director)\b'
    r'|\bto curate\b|\bkuratiert\b|nominat[ao].{0,30}curat|nombrad[ao].{0,30}comisari'
    r'|芸術監督[^。]{0,80}(?:就任|任命)|(?:任命|就任).{0,25}芸術監督|获任.{0,20}策展|[任受]命.{0,20}(?:獲|担|擔).{0,10}策展'
)
AUDIENCE = re.compile(r'visitors?[’\x27]? (?:lions|awards)|public vote|people.s choice|audience award|观众[奖獎]|観客賞')
ARCHITECTURE = re.compile(r'architecture|architettura|建築|建筑')
INSTITUTION = re.compile(r'\b(?:museums?|galleries|gallery|archives?|cinemas?|studios?|film institut\w*|film academy)\b|美術館|博物館|美术馆|博物馆|museo|museu|musée')
INSTITUTION_CHANGE = re.compile(
    r'\b(?:bankrupt\w*|shutter\w*|permanently clos\w*|ceases operations|repatriat\w*|return of stolen|'
    r'returns? stolen|appoints? (?:a |its )?(?:new )?director|appointed director|appoints?.{1,60}as director)\b'
    r'|倒産|破产|永久闭馆|永久閉館|归还文物|文物返還'
)
PROGRAMME = re.compile(
    r'\b(?:shortlist|line[- ]?up|premieres?|world premiere|opens?|opens in|new photobook|unveils|releases?)\b'
    r'|上映|(?:初|新作).{0,12}公開|(?:写真展|展覧会).{0,25}開催|开幕|首映|新作发布|estrenos?\b|estreias?\b'
)
REPORTING = re.compile(r'\b(?:interview|review|investigation|report finds)\b|\bhow\b.{0,25}\b(?:made|created|works)\b|インタビュー|対談|批評|访谈|专访|调查|crítica|entretien')
SERVICE = re.compile(
    r'^\s*(?:will|could|which|who)\b.{0,170}\?|\b(?:predictions|odds|photos of the day|what.s new on|where to watch)\b'
    r'|ott release calendar|\b(?:netflix|mubi|disney\+).{0,25}todos los estrenos'
    r'|\bwhat we.re reading\b|こちらで販売中|オンラインストア|今週末に見たい|おすすめ.{0,12}ピックアップ'
)
NAMED_AWARD = re.compile(
    r'\b(?i:wins?|won|receives?)\s+(?:[£$€]\s*[\d,.]+\s+)?(?:the\s+)?(?:20\d{2}\s+)?'
    r'(?P<name>[A-Z][\w’.-]*(?:\s+(?:[A-Z][\w’.-]*|&|of|for)){0,4})\s+(?i:award|prize)\b'
)
GENERIC_AWARD = {'best', 'first', 'grand', 'major', 'second', 'top'}


def frontpage_signals(row, rank):
    original = unicodedata.normalize('NFKC', row.get('title_original') or row.get('title_zh') or '')
    title = original.casefold()
    excerpt = unicodedata.normalize('NFKC', str(row.get('excerpt_original') or '')[:260]).casefold()
    topic = next((key for desk, key, pattern in EVENTS if desk == row.get('channel') and pattern.search(title)), None)
    if topic == 'venice' and ARCHITECTURE.search(title):
        topic = 'venice-architecture'
    action = None
    service_title = bool(SERVICE.search(title))
    if topic and not service_title and APPOINTMENT.search(title + ' ' + excerpt) and re.search(r'curat|comisari|芸術監督|策展|kuratiert', title):
        action = 'curator'
    elif topic and not service_title and RESULT.search(title):
        action = 'audience-awards' if AUDIENCE.search(title + ' ' + excerpt) else 'awards'

    if rank.get('obituary') or service_title or re.match(r"here.s what we.re reading", excerpt):
        category = 'service'
    elif action == 'curator' or (INSTITUTION.search(title) and INSTITUTION_CHANGE.search(title)):
        category = 'major'
    elif RESULT.search(title):
        category = 'outcome'
    elif PROGRAMME.search(title):
        category = 'programme'
    elif row.get('kind') in ('interview', 'work', 'photobook') or REPORTING.search(title):
        category = 'reporting'
    else:
        category = 'ordinary'
    result = {'category': category}
    story = f'{topic}:{action}' if action else None
    if not story and category == 'outcome' and (award := NAMED_AWARD.search(original)):
        name = ' '.join(award['name'].casefold().split())
        recipient = ' '.join(re.findall(r'[^\W_]+', original[:award.start()].casefold()))
        if name not in GENERIC_AWARD and recipient:
            story = f'award:{name}:{recipient}'
    if story:
        result['story'] = story
        years = set(re.findall(r'(?<!\d)20\d{2}(?!\d)', title))
        if len(years) == 1:
            result['edition_year'] = next(iter(years))
    return result


def event_days(due, instant):
    if due.get('date') and due.get('timezone'):
        try:
            day = datetime.fromisoformat(due['date']).date()
            return (day - instant.astimezone(ZoneInfo(due['timezone'])).date()).days
        except (ValueError, TypeError, KeyError):
            return None
    days = due.get('days')
    return days if type(days) in (int, float) and math.isfinite(days) else None


def same_story(first, second, hours):
    a, b = first['frontpage_editorial'], second['frontpage_editorial']
    if not a.get('story') or a['story'] != b.get('story'):
        return False
    if a.get('edition_year') and b.get('edition_year') and a['edition_year'] != b['edition_year']:
        return False
    age, other_age = first['frontpage_age_hours'], second['frontpage_age_hours']
    return age is None or other_age is None or abs(age - other_age) <= hours


def headline_ready(row):
    """A readable Chinese original or program-valid AI translation of every block."""
    from .editorial import checked_result
    import hashlib
    try:
        original = json.loads(row.get('article_blocks_json') or '[]')
        if not isinstance(original, list) or not original:
            return False
        if row.get('article_hash') and hashlib.sha256(row['article_blocks_json'].encode()).hexdigest() != row['article_hash']:
            return False
        if row.get('language') == 'zh':
            return any(b.get('type') != 'image' and str(b.get('text') or '').strip() for b in original)
        if row.get('editorial_status') not in ('reviewed', 'translated') or not row.get('editorial_title_zh'):
            return False
        translated = json.loads(row.get('editorial_blocks_json') or '[]')
        if not isinstance(translated, list):
            return False
        checked_result(row, {'title_zh': row['editorial_title_zh'],
            'excerpt_zh': row.get('editorial_excerpt_zh') or '', 'notes': [],
            'blocks': [{**b, 'index': i} for i, b in enumerate(translated)]})
        return True
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def display_title(row, headlines):
    if row.get('editorial_status') in ('reviewed', 'translated') and row.get('editorial_blocks_json') and row.get('editorial_title_zh'):
        return row['editorial_title_zh']
    translated = headlines.get(row['id'], {}).get('title_zh') or row.get('title_zh')
    if not translated and str(row.get('article_translation_provider') or '').startswith('offline-m2m100:'):
        from .autonomous_translation import machine_ready
        if machine_ready(row):
            translated = row.get('translated_title_zh')
    return translated or row.get('title_original') or '标题未取得'


def frontpage_rows(snapshot, priorities, instant, preferences=None, headlines=None, *, candidates=False):
    preferences = preferences or json.loads((ROOT / 'config/preferences.json').read_text())
    if headlines is None:
        from .headlines import load_headlines
        headlines = load_headlines({**snapshot, 'events': [e for e in snapshot.get('events', []) if e.get('title_original')]})
    cfg = preferences.get('frontpage') or {}
    lead_hours, fallback_hours = cfg.get('lead_hours', 72), cfg.get('fallback_hours', 168)
    importance = {**EDITORIAL_POINTS, **(cfg.get('editorial_points') or {})}
    freshness_hours = max(1, cfg.get('freshness_hours', 72))
    action_days = max(1, cfg.get('event_window_days', 7))
    obituary_limit = cfg.get('obituary_limit', 1)
    known, undated = [], []
    for original in snapshot.get('content', []):
        if original.get('is_demo') or original.get('evidence_status') == 'unverified':
            continue
        row = dict(original)
        rank = priorities.get(row['id'], {})
        due_days = event_days(rank.get('due') or {}, instant)
        age = None
        try:
            published = datetime.fromisoformat((row.get('published_at') or '').replace('Z', '+00:00'))
            published = published.replace(tzinfo=ZoneInfo('UTC')) if published.tzinfo is None else published
            elapsed = (instant - published).total_seconds() / 3600
            if elapsed < -2 or elapsed > fallback_hours:
                continue
            age = max(0, elapsed)
        except (ValueError, TypeError):
            if due_days is None or not (0 <= due_days <= cfg.get('undated_event_days', 2)):
                continue
        editorial = rank.get('frontpage_editorial') or frontpage_signals(row, rank)
        score = importance.get(editorial['category'], importance['ordinary'])
        if age is not None:
            score += cfg.get('freshness_points', 20) * max(0, 1 - age / freshness_hours)
        if due_days is not None and 0 <= due_days <= action_days:
            score += cfg.get('event_points', 8) * (1 - due_days / action_days)
        score -= rank.get('recommendation_penalty', 0)
        obituary = bool(rank.get('obituary'))
        if obituary:
            score -= cfg.get('obituary_penalty', 32)
        row.update(frontpage_score=score, frontpage_age_hours=age,
                   frontpage_obituary=obituary,
                   frontpage_editorial=editorial,
                   frontpage_basis='published_at' if age is not None else 'confirmed_upcoming_event')
        (known if age is not None else undated).append(row)
    readiness = {}

    def ready(row):
        if row['id'] not in readiness:
            readiness[row['id']] = headline_ready(row)
        return readiness[row['id']]

    def headline_content(row):
        return (row.get('kind') != 'industry_buzz' and not row['frontpage_obituary']
                and row['frontpage_editorial']['category'] != 'service')

    story_hours = cfg.get('story_window_hours', fallback_hours)
    order = lambda r: (-r['frontpage_score'], r['frontpage_age_hours'] if r['frontpage_age_hours'] is not None else fallback_hours, r['id'])
    versions = sorted((r for r in known + undated if r['frontpage_editorial'].get('story')),
                      key=lambda r: (not ready(r), r['frontpage_age_hours'] is None, *order(r)))
    representatives, redundant = [], set()
    for row in versions:
        if any(other.get('channel') != row.get('channel') and same_story(row, other, story_hours) for other in representatives):
            redundant.add(row['id'])
        else:
            representatives.append(row)
    known = [r for r in known if r['id'] not in redundant]
    undated = [r for r in undated if r['id'] not in redundant]
    covered = [r for r in known + undated if r['frontpage_editorial'].get('story') and headline_content(r) and ready(r)] if candidates else []

    def is_headline(row):
        if not headline_content(row):
            return False
        if not candidates:
            return ready(row)
        # Keep candidate slots for distinct editorial developments.
        already_covered = row['frontpage_editorial'].get('story') and any(
            other.get('channel') == row.get('channel') and same_story(row, other, story_hours)
            for other in covered
        )
        return not already_covered or ready(row)
    eligible = [r for r in known if is_headline(r)]
    recent = [r for r in eligible if r['frontpage_age_hours'] <= lead_hours]
    lead_pool = recent or eligible or [r for r in undated if is_headline(r)]
    if not lead_pool:
        return []
    lead = min(lead_pool, key=order)
    result, seen_ids = [lead], {lead['id']}
    def title_keys(row):
        return {unicodedata.normalize('NFKC', title).lower().strip()
                for title in (row.get('title_original'), display_title(row, headlines)) if title}

    seen_titles = title_keys(lead)
    counts = {lead.get('source_id'): 1}
    obituary_count = 0
    for channel, count in [('film', 5), ('art', 5), ('photography', 5), ('industry_buzz', 4)]:
        if channel == 'industry_buzz':
            buzz = preferences.get('industry_buzz') or {}
            if not buzz.get('enabled', True):
                continue
            share = max(0, min(1, buzz.get('max_share', 0.1)))
            if share < 1:
                count = min(count, math.floor(len(result) * share / (1 - share)))
        matches = lambda r: (r.get('kind') == 'industry_buzz' if channel == 'industry_buzz' else r.get('kind') != 'industry_buzz' and r.get('channel') == channel)
        # Unknown publication dates never outrank a dated report in the desk.
        pool = [r for r in known if matches(r)] or [r for r in undated if matches(r)]
        for index in range(count):
            pool = [r for r in pool if r['id'] not in seen_ids and seen_titles.isdisjoint(title_keys(r))
                    and not any(same_story(r, picked, story_hours) for picked in result)]
            # Only the desk's first (headline) story needs this extra gate.
            # Do not hide untranslated briefs beneath an eligible headline.
            choices = ([r for r in pool if is_headline(r)] if index == 0 and channel != 'industry_buzz'
                       else [r for r in pool if not r['frontpage_obituary'] or obituary_count < obituary_limit])
            if not choices:
                break
            row = min(choices, key=lambda r: (-(r['frontpage_score'] - counts.get(r.get('source_id'), 0) * cfg.get('source_repeat_penalty', 6)), *order(r)[1:]))
            seen_ids.add(row['id'])
            seen_titles.update(title_keys(row))
            counts[row.get('source_id')] = counts.get(row.get('source_id'), 0) + 1
            obituary_count += row['frontpage_obituary']
            result.append(row)
    return result


def headline_slots(snapshot, priorities, instant, *, candidates=False):
    rows = frontpage_rows(snapshot, priorities, instant, candidates=candidates)
    if not rows:
        return []
    result = [(rows[0]['id'], 'lead')]
    for channel in ('film', 'art', 'photography'):
        row = next((r for r in rows[1:] if r.get('channel') == channel and r.get('kind') != 'industry_buzz'), None)
        if row:
            result.append((row['id'], channel))
    return result
