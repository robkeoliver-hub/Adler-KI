import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('button_fix',ROOT/'scripts/fix_adler_button.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def prepare(tmp_path):
    root=tmp_path/'ki-adler-portaltest';css=root/m.KEY;css.parent.mkdir(parents=True)
    (root/'private').mkdir()
    new=(ROOT/'tests/fixtures/panel-pr12.css').read_bytes()
    old=new.replace(b'bottom:calc(100px + env(safe-area-inset-bottom))',b'bottom:calc(12px + env(safe-area-inset-bottom))')
    assert m.sha(old)==m.OLD and m.sha(new)==m.NEW
    css.write_bytes(old);manifest=root/'private/code-hashes.json';manifest.write_text(json.dumps({m.KEY:m.OLD,'unrelated':'keep'}))
    return root,css,manifest


def test_fix_preserves_other_hashes_and_rollback(tmp_path):
    root,css,manifest=prepare(tmp_path);before=css.read_bytes()
    m.fix(tmp_path)
    assert m.sha(css.read_bytes())==m.NEW
    assert json.loads(manifest.read_text())=={m.KEY:m.NEW,'unrelated':'keep'}
    m.fix(tmp_path)
    m.fix(tmp_path,rollback=True)
    assert css.read_bytes()==before and json.loads(manifest.read_text())[m.KEY]==m.OLD


def test_unexpected_file_is_not_changed(tmp_path):
    root,css,manifest=prepare(tmp_path);css.write_bytes(b'unexpected')
    with pytest.raises(m.FixError):m.fix(tmp_path)
    assert css.read_bytes()==b'unexpected'


def test_write_failure_restores_original(tmp_path,monkeypatch):
    root,css,manifest=prepare(tmp_path);before=css.read_bytes();old=manifest.read_bytes();real=m.write;failed=[False]
    def write(path,data):
        if path==manifest and not failed[0]:failed[0]=True;raise OSError('synthetic failure')
        real(path,data)
    monkeypatch.setattr(m,'write',write)
    with pytest.raises(OSError):m.fix(tmp_path)
    assert css.read_bytes()==before and manifest.read_bytes()==old


def test_rollback_does_not_overwrite_later_updates(tmp_path):
    root,css,manifest=prepare(tmp_path);m.fix(tmp_path)
    hashes=json.loads(manifest.read_text());hashes['unrelated']='later';manifest.write_text(json.dumps(hashes))
    with pytest.raises(m.FixError):m.fix(tmp_path,rollback=True)
    assert m.sha(css.read_bytes())==m.NEW
