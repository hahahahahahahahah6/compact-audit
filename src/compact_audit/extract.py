"""Deterministic, deliberately conservative surface-pattern extraction."""
import json
import re
from dataclasses import dataclass
from pathlib import Path

CATEGORIES = ('decision', 'constraint', 'error', 'file_edit', 'todo')
MAX_ITEMS = 500
SOURCE_LIMIT = 500


def normalize(text):
    return re.sub(r'[\W_]+', ' ', text.lower()).strip()


@dataclass(frozen=True)
class Item:
    category: str
    key: str
    text: str
    severity: str
    basename: str = ''


@dataclass
class Extraction:
    items: list
    parse_errors: int = 0
    truncated: bool = False


DECISION = re.compile(r'\b(?:decision\s*:|decided to\b|we will use\b|chosen\b|agreed to\b|going with\b)', re.I)
CONSTRAINT = re.compile(r'\b(?:must not\b|never\s+\S|do not\b|must always\b|only\s+\S|required\b)', re.I)
ERROR = re.compile(r'\b(?:error\b|traceback\b|failed\b|failed with\b|exit code\s*[:=]?\s*-?0*[1-9]\d*\b)', re.I)
EDIT = re.compile(r'\b(?:edited|changed|created|deleted|modified|wrote|rewrote|updated)\b', re.I)
PATH = re.compile(r'(?<![\w/.-])(?:[\w.-]+/)*[\w.-]+\.(?:py|js|ts|md|json|yaml|toml|go|rs)\b|(?<![\w/.-])(?:[\w.-]+/)*(?:src|tests|docs)/[\w./-]+', re.I)
TODO = re.compile(r'\b(?:todo|fixme|not done|remaining|next step|still need)\b', re.I)


def read_transcript(path):
    """Return source lines and errors; JSONL must contain objects with text."""
    path = Path(path)
    lines, errors = [], 0
    for raw in path.read_text(encoding='utf-8').splitlines():
        if not raw.strip():
            continue
        if path.suffix.lower() == '.jsonl':
            try:
                obj = json.loads(raw)
                if not isinstance(obj, dict):
                    raise ValueError('expected object')
                value = next((obj[k] for k in ('content', 'text', 'message') if k in obj), '')
                if not isinstance(value, str):
                    raise ValueError('expected text')
            except (ValueError, TypeError):
                errors += 1
                continue
            lines.extend(line for line in value.splitlines() if line.strip())
        else:
            lines.append(raw)
    return lines, errors


def extract(lines, parse_errors=0):
    items, seen = [], set()
    truncated = False
    for line in lines:
        candidates = []
        for category, pattern in (('decision', DECISION), ('constraint', CONSTRAINT), ('error', ERROR)):
            if pattern.search(line):
                key = normalize(re.sub(r'\d+', '', line) if category == 'error' else line)
                candidates.append(Item(category, key, line[:SOURCE_LIMIT], 'HIGH'))
        if EDIT.search(line):
            for match in PATH.finditer(line):
                path = match.group().rstrip('./')
                candidates.append(Item('file_edit', normalize(path), line[:SOURCE_LIMIT], 'MEDIUM', normalize(path.rsplit('/', 1)[-1])))
        if TODO.search(line):
            candidates.append(Item('todo', normalize(line), line[:SOURCE_LIMIT], 'MEDIUM'))
        for item in candidates:
            identity = (item.category, item.key)
            if identity in seen:
                continue
            seen.add(identity)
            if len(items) < MAX_ITEMS:
                items.append(item)
            else:
                truncated = True
    return Extraction(items, parse_errors, truncated)
