import hashlib
import importlib.util
import json
import stat
import zipfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('export_check', Path(__file__).resolve().parents[1] / 'scripts/check_portal_export.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_zip(tmp_path, entries):
    path = tmp_path / 'synthetic-export.zip'
    with zipfile.ZipFile(path, 'w') as z:
        for name, content in entries:
            z.writestr(name, content)
    return path


def test_source_only_archive_untouched_and_still_needs_manual_review(tmp_path):
    path = make_zip(tmp_path, [('portal/app.py', 'import os\nSECRET_KEY = os.environ["SECRET_KEY"]\n'), ('portal/templates/base.html', '<nav>synthetic</nav>')])
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    report = module.inspect_archive(path)
    assert report['ok'] and report['manual_review_required'] and report['checked'] == 2
    assert before == hashlib.sha256(path.read_bytes()).hexdigest()
    assert not (tmp_path / 'portal').exists()


@pytest.mark.parametrize('name,data,reason', [
    ('../app.py', b'', 'unsafe_path'), ('/app.py', b'', 'unsafe_path'),
    ('C:\\portal\\app.py', b'', 'unsafe_path'),
    ('uploads/REAL-NAME.jpg', b'', 'private_or_runtime_file'),
    ('config.ini', b'', 'private_or_runtime_file'), ('.env', b'', 'private_or_runtime_file'),
    ('schuetzenjugend.db', b'', 'private_or_runtime_file'), ('data.db-wal', b'', 'private_or_runtime_file'),
    ('apparently-source.py', b'SQLite format 3\x00', 'database_content'),
    ('app.py', b'password = "SYNTHETIC-SECRET-NOT-TO-PRINT"', 'literal_credential_review'),
    ('app.py', b'key = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"', 'credential_pattern'),
    ('data.sql', b'INSERT INTO users VALUES (1);', 'sql_data_export'),
    ('app.py', b'\xff', 'non_utf8'), ('nested.zip', b'', 'unreviewed_file_type'),
])
def test_unsafe_export_rejected_without_contents_or_names(tmp_path, name, data, reason):
    path = make_zip(tmp_path, [(name, data)])
    report = module.inspect_archive(path)
    assert not report['ok']
    assert reason in [x['reason'] for x in report['findings']]
    output = json.dumps(report)
    assert 'SYNTHETIC-SECRET' not in output and 'REAL-NAME' not in output and 'ghp_' not in output


def test_symlink_and_duplicate_case_paths_rejected(tmp_path):
    path = tmp_path / 'links.zip'
    with zipfile.ZipFile(path, 'w') as z:
        info = zipfile.ZipInfo('link.py')
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(info, '/etc/passwd')
        z.writestr('app.py', '')
        z.writestr('APP.PY', '')
    reasons = [x['reason'] for x in module.inspect_archive(path)['findings']]
    assert 'link_or_encrypted' in reasons and 'duplicate_path' in reasons


def test_limits_and_unreadable_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'MAX_FILES', 1)
    path = make_zip(tmp_path, [('a.py', ''), ('b.py', '')])
    assert module.inspect_archive(path)['findings'][0]['reason'] == 'archive_limit'
    bad = tmp_path / 'bad.zip';bad.write_text('SYNTHETIC-DO-NOT-PRINT')
    assert module.inspect_archive(bad)['findings'][0]['reason'] == 'unreadable_archive'

@pytest.mark.parametrize('source', [
    'app.config["SECRET_KEY"] = "SYNTHETIC-NOT-A-REAL-KEY"',
    'PASSWORD = "SYNTHETIC-NOT-A-REAL-KEY"',
    'settings = {"api_key": "SYNTHETIC-NOT-A-REAL-KEY"}',
])
def test_configuration_literal_forms_are_flagged(tmp_path, source):
    report = module.inspect_archive(make_zip(tmp_path, [('app.py', source)]))
    assert any(x['reason'] == 'literal_credential_review' for x in report['findings'])
    assert 'SYNTHETIC-NOT-A-REAL-KEY' not in json.dumps(report)


def test_known_export_redaction_is_placeholder_not_release_approval(tmp_path):
    report = module.inspect_archive(make_zip(tmp_path, [('app.py', 'SECRET_KEY = "REDACTED_FOR_CODEX"')]))
    assert report['ok'] and report['manual_review_required']
