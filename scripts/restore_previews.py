"""Restore lossless preview PNGs shipped as base64; optional, not used by the app."""
from pathlib import Path
import base64
import hashlib

EXPECTED = {
'preview-chromium-375.png': '60c688e63269e46dfebba3d6e9a42a9a6549b78d8c6209609ebd9bdb171569e2',
'preview-chromium-1280.png': '830d4143b249e664703cff779748ee428f778e136c0ca6dfba3994835c3e756c',
}
root = Path(__file__).resolve().parent.parent / 'docs'
for name, digest in EXPECTED.items():
    data = base64.b64decode((root / (name + '.base64')).read_text(), validate=False)
    if hashlib.sha256(data).hexdigest() != digest:
        raise SystemExit('Preview checksum mismatch')
    target = root / name
    if target.exists() and target.read_bytes() != data:
        raise SystemExit('Refusing to overwrite a different preview')
    target.write_bytes(data)
    print(name)
