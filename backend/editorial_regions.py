"""Field-specific editorial attention, source diversity and honest coverage evidence."""
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def policy():
    return json.loads((ROOT / 'config/editorial-regions.json').read_text())


def country_tier(country, channel, rules=None):
    rules = rules or policy()
    field = rules['channels'].get(channel, {})
    return next((tier for tier in (1, 2) if country in field.get('tier_' + str(tier), [])), rules['default_tier'])


def source_tier(source, channel=None, rules=None):
    rules = rules or policy()
    focus = source.get('editorial_focus', {})
    if focus.get('role') == 'global_core':
        return 1
    # Deliberate source assignments are not an inference from publisher headquarters.
    return min((country_tier(code, field, rules) for code in focus.get('countries', [])
                for field in ([channel] if channel else source.get('channels', []))), default=rules['default_tier'])


def ordered_sources(sources, rules=None):
    rules = rules or policy()
    # Sorting only: every enabled source is still fetched, regardless of its tier.
    sources = sorted(sources, key=lambda s: (source_tier(s, rules=rules), -media_weight(s)))
    catalog = {s['id']: s for s in sources}
    rows = [{'id': s['id'], 'source_id': s['id']} for s in sources]
    return [catalog[row['id']] for row in _regional_pick(rows, len(rows), catalog, rules)]


def media_weight(source, lane='regional'):
    weights = source.get('editorial_focus', {}).get('media_weight', {})
    if lane == 'global':
        return weights.get('international', 50)
    if lane == 'discovery':
        return weights.get('discovery', 50)
    return weights.get('local_specialist', 50)


def international_gateway(source, rules):
    return source.get('editorial_focus', {}).get('role') == 'global_core' or media_weight(source, 'global') >= rules['media_weights']['international_gateway_threshold']


def row_focus(row, source, rules):
    """Use documented subject geography when known; never publisher country."""
    try:
        places = json.loads(row.get('locations_json') or '[]')
    except (ValueError, TypeError):
        places = []
    countries = {p.get('country') for p in places if isinstance(p, dict) and p.get('country')}
    if row.get('country'):
        countries.add(row['country'])
    countries.discard('GLOBAL')
    field = row.get('channel') or (source.get('channels') or ['art'])[0]
    if countries:
        country = min(sorted(countries), key=lambda code: country_tier(code, field, rules))
        area = next((region['id'] for region in rules['world_regions'] if country in region['countries']), 'global')
        return area, country_tier(country, field, rules), 'reported_geography'
    focus = source.get('editorial_focus', {})
    area = 'global' if focus.get('role') == 'global_core' else (focus.get('regions') or ['global'])[0]
    return area, source_tier(source, field, rules), 'source_assignment_only'


def _regional_pick(rows, count, catalog, rules, lane='regional'):
    """Region attention first, then independent media weights within each region."""
    if count <= 0:
        return []
    areas, area_tiers = {}, {}
    for row in rows:
        area, tier, _ = row_focus(row, catalog.get(row['source_id'], {}), rules)
        if lane == 'global':
            area = 'global'
        areas.setdefault(area, {}).setdefault(row['source_id'], []).append(row)
        area_tiers[area] = min(area_tiers.get(area, 3), tier)
    ordered = sorted(areas, key=lambda area: area_tiers[area])
    # Tier 1 receives three turns, tier 2 two, discovery one; every desk gets a turn.
    turns = ordered + [area for area in ordered if area_tiers[area] <= 2] + [area for area in ordered if area_tiers[area] == 1]
    served, selected = Counter(), []
    def weight(identifier):
        source = catalog.get(identifier, {})
        mode = 'global' if source.get('editorial_focus', {}).get('role') == 'global_core' else lane
        return media_weight(source, mode)
    while areas and len(selected) < count:
        for area in turns:
            groups = areas.get(area)
            if not groups:
                continue
            sid = min(groups, key=lambda sid: (served[sid] / max(1, weight(sid)), -weight(sid)))
            selected.append(groups[sid].pop(0))
            served[sid] += 1
            if not groups[sid]:
                del groups[sid]
            if not groups:
                del areas[area]
            if len(selected) >= count:
                break
    return selected


def body_batch(fresh, rechecks, catalog, limit, rules=None):
    """Protect headlines/major news, then share body-fetch slots across source desks."""
    from .priority import priority_key
    if limit <= 0:
        return []
    rules = rules or policy()
    def ordering(row):
        key = priority_key(row)
        _, tier, _ = row_focus(row, catalog.get(row['source_id'], {}), rules)
        return key[:5] + (tier,) + key[5:]
    fresh = sorted(fresh, key=ordering)
    heads = [r for r in fresh if 'headline_order' in r.get('translation_priority', {})][:limit]
    budget = min(limit, max(len(heads), limit - min(10, limit // 4)))
    selected = list(heads)
    seen = {r['id'] for r in selected}
    for row in fresh:
        rank = row.get('translation_priority', {})
        if len(selected) >= budget:
            break
        if row['id'] not in seen and (rank.get('importance') == 'high' or rank.get('priority') == 'P0'):
            selected.append(row)
            seen.add(row['id'])
    # Named source units use a protected slice inside the existing discovery budget.
    from .attention_units import reserved_units
    units = reserved_units(catalog)
    if sum(u['share'] for u in units) > rules['collection']['discovery_share']:
        raise ValueError('attention_units_exceed_discovery_budget')
    unit_ids = set().union(*(u['source_ids'] for u in units)) if units else set()
    for unit in units:
        done = sum(r['source_id'] in unit['source_ids'] for r in selected)
        slots = min(budget - len(selected), max(0, math.ceil(budget * unit['share']) - done))
        candidates = [r for r in fresh if r['id'] not in seen and r['source_id'] in unit['source_ids']]
        picks = _regional_pick(candidates, slots, catalog, rules, 'discovery')
        selected.extend(picks)
        seen.update(r['id'] for r in picks)
    discovery = [r for r in fresh if r['id'] not in seen and catalog.get(r['source_id'], {}).get('editorial_focus', {}).get('role') == 'discovery']
    discovery_done = sum(r['source_id'] in unit_ids or catalog.get(r['source_id'], {}).get('editorial_focus', {}).get('role') == 'discovery' for r in selected)
    count = min(budget - len(selected), max(0, math.ceil(budget * rules['collection']['discovery_share']) - discovery_done))
    rotated = _regional_pick([r for r in discovery if r['source_id'] not in unit_ids], count, catalog, rules, 'discovery')
    if len(rotated) < count:
        rotated.extend(_regional_pick([r for r in discovery if r['source_id'] in unit_ids], count - len(rotated), catalog, rules, 'discovery'))
    selected.extend(rotated)
    seen.update(r['id'] for r in rotated)
    # International media have their own lane, independent of the host country's tier.
    global_target = math.ceil(budget * rules['media_weights']['global_lane_share'])
    global_done = sum(international_gateway(catalog.get(r['source_id'], {}), rules) for r in selected)
    global_rows = [r for r in fresh if r['id'] not in seen and international_gateway(catalog.get(r['source_id'], {}), rules)]
    gateways = _regional_pick(global_rows, min(budget - len(selected), max(0, global_target - global_done)), catalog, rules, 'global')
    selected.extend(gateways)
    seen.update(r['id'] for r in gateways)
    selected.extend(_regional_pick([r for r in fresh if r['id'] not in seen], budget - len(selected), catalog, rules))
    seen = {r['id'] for r in selected}
    # Keep cached-body rechecks and use any unused recheck slots for fresh bodies.
    remainder = rechecks + [r for r in fresh if r['id'] not in seen]
    selected.extend(remainder[:limit - len(selected)])
    return selected


def regional_coverage(snapshot, config, audit=None):
    rules = policy()
    sources = [s for s in config['sources'] if s.get('enabled')]
    checks = {c['source_id']: c for c in (audit or {}).get('sources', [])}
    inventory = Counter(row['source_id'] for row in snapshot.get('content', []) if not row.get('is_demo'))
    matrix, priority_gaps = [], []
    for region in rules['world_regions']:
        fields = {}
        for channel in rules['channels']:
            assigned = [s for s in sources if channel in s['channels'] and region['id'] in s.get('editorial_focus', {}).get('regions', [])]
            for country in region['countries']:
                if country_tier(country, channel, rules) == 1 and not any(channel in s['channels'] and country in s.get('editorial_focus', {}).get('countries', []) for s in sources):
                    priority_gaps.append({'country': country, 'channel': channel, 'reason': 'no_country_specific_source_assignment'})
            fields[channel] = {'target_country_tiers': {code: country_tier(code, channel, rules) for code in region['countries']},
                               'source_ids': [s['id'] for s in assigned],
                               'rss_sources': sum(s.get('adapter') == 'rss' for s in assigned),
                               'successful_rss_checks': sum(checks.get(s['id'], {}).get('status') == 'checked' for s in assigned if s.get('adapter') == 'rss'),
                               'failed_source_ids': [s['id'] for s in assigned if checks.get(s['id'], {}).get('status') in ('failed', 'partial')],
                               'inventory_from_assigned_sources': sum(inventory[s['id']] for s in assigned),
                               'coverage_status': 'assigned_sources_only' if assigned else 'no_dedicated_source'}
        matrix.append({'id': region['id'], 'label': region['label'], 'channels': fields})
    return {'policy_path': 'config/editorial-regions.json', 'tiers': rules['tiers'],
            'default_tier_for_any_unlisted_country': rules['default_tier'],
            'source_focus_is_editorial_assignment_not_reported_geography': True,
            'priority_country_gaps': priority_gaps,
            'source_weights': [{'id': s['id'], 'publisher_country': s.get('publisher_country'), 'editorial_focus': s.get('editorial_focus'), 'tiers_by_field': {field: source_tier(s, field, rules) for field in s['channels']}} for s in sources],
            'international_gateway_source_ids': [s['id'] for s in sources if international_gateway(s, rules)],
            'weights_are_editorial_settings_not_measured_audience_share': True,
            'matrix': matrix, 'unlocated_content': sum(not r.get('country') and not json.loads(r.get('locations_json') or '[]') for r in snapshot.get('content', []) if not r.get('is_demo')),
            'discovery_share_of_available_new_body_slots': rules['collection']['discovery_share'],
            'global_completeness': 'unknown', 'limitations': rules['limitations']}
