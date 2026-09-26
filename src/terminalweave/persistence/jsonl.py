from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
import json, os, tempfile
from terminalweave.core.errors import ValidationError

@dataclass(frozen=True)
class JsonLineRecord:
    kind: str
    key: str
    payload: dict[str, object]

class JsonLineStore:

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = RLock()

    def append(self, record: JsonLineRecord) -> None:
        if not record.kind or not record.key:
            raise ValidationError('record kind and key required')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({'kind': record.kind, 'key': record.key, 'payload': record.payload}, sort_keys=True, separators=(',', ':'), default=str)
        with self._lock:
            with self.path.open('a', encoding='utf-8') as f:
                f.write(line + '\n')
                f.flush()
                os.fsync(f.fileno())

    def read_all(self) -> list[JsonLineRecord]:
        if not self.path.exists():
            return []
        out = []
        with self._lock:
            for number, line in enumerate(self.path.read_text(encoding='utf-8').splitlines(), start=1):
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValidationError(f'invalid JSONL at line {number}') from exc
                out.append(JsonLineRecord(str(data['kind']), str(data['key']), dict(data['payload'])))
        return out

    def compact_latest(self) -> int:
        rows = self.read_all()
        latest = {}
        for row in rows:
            latest[row.kind, row.key] = row
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=self.path.name, dir=str(self.path.parent))
        os.close(fd)
        tmp_path = Path(tmp)
        try:
            with tmp_path.open('w', encoding='utf-8') as f:
                for row in sorted(latest.values(), key=lambda r: (r.kind, r.key)):
                    f.write(json.dumps({'kind': row.kind, 'key': row.key, 'payload': row.payload}, sort_keys=True, separators=(',', ':'), default=str) + '\n')
            os.replace(tmp_path, self.path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
        return len(rows) - len(latest)
