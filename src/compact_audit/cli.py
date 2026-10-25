"""Command-line interface."""
import argparse
import json
from pathlib import Path
from . import __version__
from .audit import audit
from .extract import extract, read_transcript


def main(argv=None):
    parser = argparse.ArgumentParser(prog='compact-audit', description='Offline surface audit of compaction context loss.')
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('audit', help='compare a transcript with its summary')
    command.add_argument('transcript', type=Path)
    command.add_argument('summary', type=Path)
    command.add_argument('--json', action='store_true', dest='json_output')
    command.add_argument('--min-severity', choices=('high', 'medium'), default='high')
    args = parser.parse_args(argv)
    try:
        lines, errors = read_transcript(args.transcript)
        report = audit(extract(lines, errors), args.summary.read_text(encoding='utf-8'), args.min_severity)
    except (OSError, UnicodeError) as exc:
        parser.error(str(exc))
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print('{verdict}: {kept} kept, {dropped_count} dropped / {total_items} items'.format(**report))
        for category, counts in report['totals'].items():
            print('{}: {} kept, {} dropped'.format(category, counts['kept'], counts['dropped']))
        print('Parse errors: {}'.format(report['parse_errors']))
        print('Truncated: {} (maximum 500 items)'.format(report['truncated']))
        for item in report['dropped']:
            print('DROPPED [{severity}] {category}: {key}\n  {text}'.format(**item))
        print(report['limitation'])
    return report['exit_code']
