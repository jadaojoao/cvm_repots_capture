# -*- coding: utf-8 -*-
"""
src/db.py — Factory de conexão ao banco com 3-tier fallback:
  1. os.getenv("DATABASE_URL")  → Supabase / PostgreSQL remoto
  2. SQLite local               → desenvolvimento sem configuração extra

Extraído de dashboard/db.py. Dependência de streamlit removida —
scripts CLI e o app PyQt6 podem importar sem instalar o Streamlit.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, Engine

_SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "db" / "cvm_financials.db"
_SQLITE_URL  = f"sqlite:///{_SQLITE_PATH}"


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = _resolve_url()
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
    )


def _resolve_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url:
        return url
    return _SQLITE_URL
