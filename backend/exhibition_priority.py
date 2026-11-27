"""Programme evidence and display groups for the exhibition catalogue."""
import json
import re
import unicodedata
from collections import defaultdict
from urllib.parse import urlsplit

from .exhibitions import normalized
from .storage import ROOT

POLICY = ROOT / 'config/exhibition-priority.json'
SEASONAL_PREFIX = re.compile(r'^(?:(?:春|夏|秋|冬)(?:季)?の)?(?:特別企画展|特別陳列|特別展|企画展|展覧会)[\s:・「『【(\[]*')
DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
MAJOR_EXHIBITION_LEVELS = {'rarity': 1, 'curation': 2, 'reach': 1}
# Each signal describes a programme. Format labels such as 芸術祭 and 企画展 stay in the source data.
PROGRAMMES = (
    (3, '国际艺术节或三年展', re.compile(r'国際(?:芸術祭|アートフェスティバル|ビエンナーレ|トリエンナーレ)|international (?:art )?(?:festival|biennale|biennial|triennial)', re.I), {'rarity': 1, 'curation': 1, 'reach': 2}),
    (3, '开馆纪念展', re.compile(r'開館記念(?:特別)?展(?![\dIVX])', re.I), {'rarity': 2, 'curation': 1, 'reach': 1}),
    (3, '大型回顾展', re.compile(r'大回顧展|(?:過去最大|大規模).{0,16}回顧展|major retrospective', re.I), MAJOR_EXHIBITION_LEVELS),
    (2, '回顾展', re.compile(r'回顧展|\bretrospective\b', re.I), {'curation': 2}),
    (2, '纪念专题', re.compile(r'(?:生誕|没後)\s*[1-9]\d{1,2}\s*周年'), {'curation': 2}),
    (1, '场馆周年专题', re.compile(r'(?:開館|創立)\s*[1-9]\d*\s*周年記念'), {'curation': 1}),
    (1, '特别展', re.compile(r'特別展|特別企画展'), {'curation': 1}),
)
OFFICIAL_INTRO_PROGRAMME = re.compile(
    r'(?:本展(?:覧会)?|この展覧会)[はが][^。！？]{0,140}?'
    r'(?:(?P<retrospective>大回顧展|(?:過去最大|大規模)[^。！？]{0,16}回顧展)'
    r'|(?P<first_major>初の大規模[^。！？]{0,16}展))'
    r'(?:です|となります)\s*(?:。|$)'
)
EVENT_LABELS = {'講座': '讲座', '連続講座': '讲座', '講演会': '讲座', 'トークイベント': '讲座',
                'ワークショップ': '工作坊', 'シンポジウム': '座谈会'}
EVENT_TITLE = re.compile(r'^(' + '|'.join(EVENT_LABELS) + r')(?:[\s:「『【(]|$)')
EXHIBITION_TITLE = re.compile(r'展示|展覧会|企画展|特別展|個展|回顧展|作品展|美術展')


def edition_text(title):
    return unicodedata.normalize('NFKC', title or '').strip(' 「『【')


def edition_key(row, review):
    start, end = row.get('start_date') or '', row.get('end_date') or ''
    title = normalized(SEASONAL_PREFIX.sub('', edition_text(row.get('title_original'))))
    if row.get('venue_id') and DATE.fullmatch(start) and DATE.fullmatch(end) and not row.get('date_conflict'):
        if review and len(review['ids']) > 1:
            return 'review', review['ids'][0], row['venue_id'], start, end
        if len(title) >= 8:
            return 'edition', row['venue_id'], start, end, title
    return 'record', row['id']


def observations(row):
    return row.get('evidence') or [{
        'title': row.get('title_original'), 'url': row.get('evidence_url'), 'source': row.get('source_id'),
        'official': row.get('official'),
    }]


def hosts(evidence):
    return {host.removeprefix('www.') for item in evidence
            if (host := urlsplit(item.get('url') or '').hostname)}


def related_event(row, evidence):
    if not row.get('start_date') or row['start_date'] != row.get('end_date'):
        return None
    for item in evidence:
        title = edition_text(item.get('title'))
        if EXHIBITION_TITLE.search(title):
            continue
        label = EVENT_TITLE.match(title)
        if label:
            return EVENT_LABELS[label[1]]
        for tag in item.get('labels', []):
            if tag in EVENT_LABELS:
                return EVENT_LABELS[tag]
    return None


def official_intro_programme(members, introductions):
    for row in members:
        intro = introductions.get(row['id'], {})
        if intro.get('status') != 'introduction':
            continue
        url, source = intro.get('url'), intro.get('source')
        if not url or not source or not any(
            item.get('official') and not item.get('shared_index_url')
            and item.get('url') == url and item.get('source') == source
            for item in observations(row)
        ):
            continue
        # Limit the match to a sentence describing the current exhibition.
        for paragraph in intro.get('paragraphs', [])[:12]:
            if match := OFFICIAL_INTRO_PROGRAMME.search(edition_text(paragraph)):
                label = '大型回顾展' if match.group('retrospective') else '首次大型展览'
                return {'programme': 3, 'reason': label + '，场馆本届展览介绍确认。', 'url': url}
    return {}


def importance_score(scoring, levels, assessment=None):
    if assessment is not None:
        if set(assessment) != set(scoring['dimensions']) or any(not fact.get('reason') for fact in assessment.values()):
            raise ValueError('exhibition_importance_assessment_requires_all_evidence')
        levels = {key: fact['level'] for key, fact in assessment.items()}
    breakdown = []
    for key, dimension in scoring['dimensions'].items():
        level = levels.get(key, 0)
        if type(level) is not int or not 0 <= level <= 3:
            raise ValueError('invalid_exhibition_importance_level')
        item = {'label': dimension['label'], 'weight': dimension['weight'], 'level': level}
        if assessment:
            item['reason'] = assessment[key]['reason']
        breakdown.append(item)
    score = round(sum(item['weight'] * item['level'] for item in breakdown) / 3)
    tier = 3 if score >= scoring['major_min'] else 2 if score >= scoring['thematic_min'] else 1
    return {'tier': tier, 'importance_score': score, 'importance_assessment': breakdown}


def programme_grade(members, evidence, verified, introductions, scoring):
    support = min(2, max(0, len(hosts(evidence)) - 1)) + int(any(item.get('official') for item in evidence) or bool(verified))
    if verified:
        return {**importance_score(scoring, MAJOR_EXHIBITION_LEVELS, verified.get('assessment')),
                'programme': verified.get('programme', 3), 'support': support,
                'reason': verified['reason'], 'url': verified['url']}
    result = {'tier': 1, 'programme': 0, 'support': support, 'importance_score': 0}
    if any('permanent' in row.get('flags', ()) for row in members):
        return {**result, 'tier': 0}
    best = result
    for strength, label, pattern, levels in PROGRAMMES:
        matching = [item for item in evidence if pattern.search(edition_text(item.get('title')))]
        if not matching:
            continue
        official = next((item for item in matching if item.get('official')), None)
        confirmed = bool(official) or len(hosts(matching)) >= 2
        if strength == 1 and not confirmed:
            continue
        score = importance_score(scoring, levels if confirmed else {'curation': min(2, strength)})
        if score['importance_score'] <= best['importance_score']:
            continue
        reason = label + ('，场馆官网确认。' if official else '，多个来源佐证。' if confirmed else '，来源展讯注明。')
        best = {**result, **score, 'programme': strength, 'reason': reason, 'url': (official or matching[0]).get('url')}
    if confirmed_intro := official_intro_programme(members, introductions):
        score = importance_score(scoring, MAJOR_EXHIBITION_LEVELS)
        if score['importance_score'] > best['importance_score']:
            return {**result, **confirmed_intro, **score}
    return best


def add_recommendations(items, policy=None, *, introductions=None):
    """Annotate public copies while retaining every source row and its reading URL."""
    if policy is None or 'importance' not in policy:
        policy = {**json.loads(POLICY.read_text(encoding='utf-8')), **(policy or {})}
    scoring = policy['importance']
    weights = [axis['weight'] for axis in scoring['dimensions'].values()]
    if (sum(weights) != 100 or any(type(weight) is not int or weight <= 0 for weight in weights)
            or not 0 < scoring['thematic_min'] < scoring['major_min'] <= 100):
        raise ValueError('invalid_exhibition_importance_weights_or_thresholds')
    introductions = introductions or {}
    reviews = {identifier: entry for group in ('verified_programmes', 'related_events')
               for entry in policy[group] for identifier in entry['ids']}
    groups = defaultdict(list)
    for row in items.values():
        review = reviews.get(row['id'])
        if review and (review['start_date'], review['end_date']) != (row.get('start_date'), row.get('end_date')):
            review = None
        groups[edition_key(row, review)].append((row, review))
    for group in groups.values():
        members = [row for row, _ in group]
        evidence = [item for row in members for item in observations(row)]
        ordered = sorted(members, key=lambda row: (
            not row.get('official'), -len(observations(row)), not row.get('image_url'),
            not (set(row.get('types', ())) - {'other'}), row['id'],
        ))
        review = next((review for _, review in group if review), None)
        label = review.get('label') if review else related_event(ordered[0], evidence)
        recommendation = programme_grade(members, evidence, review, introductions, scoring) if not label else None
        for row in members:
            row['recommendation'] = recommendation
            if len(members) > 1:
                row['duplicate_group'] = ordered[0]['id']
                own_urls = {item.get('url') for item in observations(row)}
                others = {item['url']: item for item in evidence if item.get('url') and item['url'] not in own_urls}
                row['related_sources'] = [{key: item[key] for key in ('url', 'source', 'official', 'date_text') if key in item}
                                          for item in others.values()]
            if label:
                row['related_event'] = label
