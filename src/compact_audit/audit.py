"""Audit literal normalized surfaces, never semantic equivalence."""
from dataclasses import asdict
import re
from .extract import CATEGORIES, normalize

LIMITATION = 'Surface matching only. DROPPED means not found by surface matching — verify manually. Paraphrase is not detected; severity is a triage signal, not a verdict about meaning.'


def audit(extraction, summary, min_severity='high'):
    if min_severity not in ('high', 'medium'):
        raise ValueError('min_severity must be high or medium')
    normalized = normalize(summary)
    error_summary = normalize(re.sub(r'\d+', '', summary))
    totals = {category: {'kept': 0, 'dropped': 0} for category in CATEGORIES}
    dropped = []
    for item in extraction.items:
        target = error_summary if item.category == 'error' else normalized
        kept = bool(item.key and item.key in target)
        if item.category == 'file_edit':
            kept = kept or bool(item.basename and item.basename in target)
        totals[item.category]['kept' if kept else 'dropped'] += 1
        if not kept:
            dropped.append(asdict(item))
    severe = any(item['severity'] == 'HIGH' or min_severity == 'medium' for item in dropped)
    exit_code = 2 if extraction.parse_errors or severe else (1 if dropped else 0)
    return {
        'totals': totals, 'total_items': len(extraction.items),
        'kept': len(extraction.items) - len(dropped), 'dropped_count': len(dropped),
        'dropped': dropped, 'parse_errors': extraction.parse_errors,
        'truncated': extraction.truncated, 'min_severity': min_severity,
        'verdict': {0: 'PASS', 1: 'WARN', 2: 'FAIL'}[exit_code],
        'exit_code': exit_code, 'limitation': LIMITATION,
    }
