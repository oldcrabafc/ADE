from __future__ import annotations

import hashlib
from pathlib import Path

from .constants import CLIENTS_DIR, DEFAULT_DB_NAME


def client_slug(client_name: str) -> str:
    digest = hashlib.sha1(client_name.strip().encode("utf-8")).hexdigest()[:8]
    return f"client_{digest}"


def resolve_client_dir(client_name: str) -> Path:
    path = CLIENTS_DIR / client_slug(client_name)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_client_db_path(client_name: str) -> Path:
    return resolve_client_dir(client_name) / DEFAULT_DB_NAME
