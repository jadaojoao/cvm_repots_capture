# -*- coding: utf-8 -*-
"""
src/db.py — Factory de conexão ao banco com 3-tier fallback:
  1. os.getenv("DATABASE_URL")  → Supabase / PostgreSQL remoto
  2. SQLite local               → desenvolvimento sem configuração extra

Extraído de dashboard/db.py. Dependência de streamlit removida —
scripts CLI e o app PyQt6 podem importar sem instalar o Streamlit.
"""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine, Engine

from src.settings import AppSettings, get_settings


def build_engine(settings: AppSettings | None = None) -> Engine:
    cfg = settings or get_settings()
    url = _resolve_url(cfg)
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return build_engine(get_settings())


def _resolve_url(settings: AppSettings) -> str:
    if settings.database_url:
        return settings.database_url
    return settings.paths.sqlite_url
