"""Release only operator-verified zero-call reservations, never unknown crashes."""
import json
import re
from pathlib import Path
from .autonomous_translation import write_json


def release_verified_unused(ledger, proofs):
    released = []
    for proof in proofs:
        key = proof.get('reservation_id', '')
        report = proof.get('report') or {}
        if (not re.fullmatch(r'\d+:\d+', key) or proof.get('run_conclusion') != 'failure'
                or type(report.get('requests')) is not int or report['requests'] != 0
                or report.get('account_mode') != 'free-project-only'
                or not report.get('finished_at') or not proof.get('evidence_url')):
            continue
        entry = (ledger.get('reservations') or {}).get(key) or {}
        allocated = entry.get('allocated')
        if (entry.get('status') != 'reserved' or type(allocated) is not int or allocated <= 0
                or allocated != proof.get('allocated') or entry.get('remaining') != allocated
                or entry.get('day') != proof.get('day')):
            continue
        usage = ledger['days'][entry['day']]
        if type(usage.get('reserved_requests')) is not int or usage['reserved_requests'] < allocated:
            raise ValueError('inconsistent_reserved_request_ledger')
        usage['reserved_requests'] -= allocated
        entry.update(remaining=0, actual_requests=0, status='closed',
                     unused_release_evidence=proof['evidence_url'])
        released.append(key)
    return released


def apply_verified_repairs(path, directory):
    path, directory = Path(path), Path(directory)
    if not path.exists(): return []
    proofs = [json.loads(p.read_text()) for p in directory.glob('*.json')
              if re.fullmatch(r'\d+-\d+\.json', p.name)]
    ledger = json.loads(path.read_text())
    released = release_verified_unused(ledger, proofs)
    if released: write_json(path, ledger)
    return released
