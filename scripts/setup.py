#!/usr/bin/env python3
"""Create private demo configuration once. Never replace existing configuration."""
import os
import secrets
from pathlib import Path
root = Path(__file__).resolve().parent.parent
path = root / 'config.ini'
if path.exists():
    raise SystemExit('config.ini existiert bereits; unverändert.')
text = (root / 'config.example.ini').read_text().replace('HIER_EIGENEN_LANGEN_ZUFALLSCODE_EINTRAGEN', secrets.token_urlsafe(24))
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as file: file.write(text)
print('Private config.ini erstellt. Zugangscode dort lokal ablesen; nicht veröffentlichen.')
