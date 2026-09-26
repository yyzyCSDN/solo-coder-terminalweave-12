from __future__ import annotations
import argparse, json
from datetime import datetime, timedelta, timezone
from terminalweave.marine.tide import TideCurve, TideSample, UnderKeelRequirement
from terminalweave.api.http import serve
UTC = timezone.utc

def demo() -> dict[str, object]:
    start = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    curve = TideCurve([TideSample(start, 1.0), TideSample(start + timedelta(hours=6), 2.5)])
    req = UnderKeelRequirement(12.0, 11.5, 1.0)
    at = start + timedelta(hours=3)
    return {'project': 'TerminalWeave', 'tide_height_m': round(curve.height_at(at), 3), 'clearance_m': round(curve.clearance_m(at, req), 3), 'safe': curve.is_safe(at, req)}

def main(argv: list[str] | None=None) -> int:
    parser = argparse.ArgumentParser(prog='terminalweave')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    http = sub.add_parser('serve')
    http.add_argument('--host', default='127.0.0.1')
    http.add_argument('--port', type=int, default=8080)
    args = parser.parse_args(argv)
    if args.command == 'demo':
        print(json.dumps(demo(), sort_keys=True))
        return 0
    if args.command == 'serve':
        serve(args.host, args.port)
        return 0
    return 2
if __name__ == '__main__':
    raise SystemExit(main())
