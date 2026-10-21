"""Read-only ZIP preflight. Never extracts, imports code or prints source/secrets.

An OK result only covers technical checks/patterns, never proves absence of PII.
Every export requires human review before transfer. No archive is modified.
"""
import argparse
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_FILES = 1000
MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 20 * 1024 * 1024
ALLOWED = {'.py', '.html', '.css', '.js', '.json', '.md', '.txt', '.sql', '.example', '.service', '.sh', '.webmanifest'}
SECRET = re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
ASSIGNMENT = re.compile(rb'''(?im)(?:secret_key|api_key|password|passwort|demo_code|qr_token)[\"\'\]]*\s*[=:]\s*["']([^"'\r\n]+)["']''')
PLACEHOLDERS = {b'', b'example', b'placeholder', b'changeme', b'REDACTED', b'<REDACTED>', b'REDACTED_FOR_CODEX'}


def inspect_archive(path):
    issues = []
    checked = 0
    def issue(index, reason):
        # Index only: filenames themselves can contain real names or URL tokens.
        issues.append({'entry': index, 'reason': reason})
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_FILES or sum(e.file_size for e in entries) > MAX_TOTAL:
                issue(0, 'archive_limit')
                return {'ok': False, 'checked': 0, 'findings': issues, 'manual_review_required': True}
            seen = set()
            for index, entry in enumerate(entries, 1):
                name = entry.filename
                parts = PurePosixPath(name).parts
                if ('\\' in name or ':' in name or name.startswith('/') or '..' in parts
                        or any(ord(c) < 32 for c in name)):
                    issue(index, 'unsafe_path'); continue
                key = name.casefold().rstrip('/')
                if key in seen:
                    issue(index, 'duplicate_path'); continue
                seen.add(key)
                if stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                    issue(index, 'link_or_encrypted'); continue
                lower = [p.casefold() for p in parts]
                leaf = lower[-1] if lower else ''
                if (any(p in {'.git', '.venv', 'venv', '__pycache__', 'uploads', 'backups'} for p in lower)
                        or leaf.startswith('.env') or leaf in {'config.ini', 'credentials', 'id_rsa', 'id_ed25519'}
                        or Path(leaf).suffix in {'.db', '.sqlite', '.sqlite3', '.key', '.pem', '.log'}
                        or any(leaf.endswith(s) for s in ('.db-wal', '.db-shm', '.sqlite-wal', '.sqlite-shm'))):
                    issue(index, 'private_or_runtime_file'); continue
                if entry.is_dir():
                    continue
                if entry.file_size > MAX_FILE or (entry.file_size > 100000 and entry.file_size > max(1, entry.compress_size) * 200):
                    issue(index, 'file_limit'); continue
                if Path(leaf).suffix not in ALLOWED:
                    issue(index, 'unreviewed_file_type'); continue
                with archive.open(entry) as source:
                    data = source.read(MAX_FILE + 1)
                if len(data) > MAX_FILE:
                    issue(index, 'file_limit'); continue
                checked += 1
                if data.startswith(b'SQLite format 3\x00'):
                    issue(index, 'database_content'); continue
                try:
                    data.decode('utf-8')
                except UnicodeError:
                    issue(index, 'non_utf8'); continue
                if SECRET.search(data):
                    issue(index, 'credential_pattern')
                if any(m.group(1) not in PLACEHOLDERS for m in ASSIGNMENT.finditer(data)):
                    issue(index, 'literal_credential_review')
                if Path(leaf).suffix == '.sql' and re.search(rb'(?i)\b(?:INSERT\s+INTO|COPY\s+.+?\s+FROM)\b', data):
                    issue(index, 'sql_data_export')
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError):
        issue(0, 'unreadable_archive')
    return {'ok': not issues, 'checked': checked, 'findings': issues, 'manual_review_required': True}


def main():
    parser = argparse.ArgumentParser(description='Lokale Nur-Lese-Prüfung eines bereinigten Portal-ZIP-Exports')
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    report = inspect_archive(args.archive)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    raise SystemExit(0 if report['ok'] else 2)


if __name__ == '__main__':
    main()
