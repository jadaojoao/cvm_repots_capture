# -*- coding: utf-8 -*-
"""
database/db.py — Connection factory com 3-tier fallback:
  1. st.secrets["database"]["url"]  → Streamlit Community Cloud (produção)
  2. os.getenv("DATABASE_URL")       → scraper local apontando Supabase
  3. SQLite local                    → desenvolvimento sem configuração extra
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
        pool_pre_ping=True,   # detecta conexões mortas (Supabase fecha idle após 5 min)
        pool_recycle=300,
    )


def _resolve_url() -> str:
    # 1) Streamlit Cloud secrets
    try:
        import streamlit as st
        url = st.secrets["database"]["url"]
        if url:
            return url
    except Exception:
        pass

    # 2) Variável de ambiente (scraper local → Supabase)
    url = os.getenv("DATABASE_URL", "")
    if url:
        return url

    # 3) SQLite local (fallback padrão)
    return _SQLITE_URL
