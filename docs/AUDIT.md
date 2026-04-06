# AUDIT.md — Project Audit & Cleanup Record

**Date:** 2026-04-01
**Scope:** Scripts, dashboard modules, tests, documentation
**Status:** Historical record of the cleanup pass. This file is not the current-state source of truth.

---

## Findings Summary

### Scripts (62 total → 21 active, 41 archived)

| Category | Count | Action |
|---|---|---|
| Core batch & update | 4 | Keep |
| DB setup & maintenance | 3 | Keep |
| Analysis & KPI | 2 | Keep |
| Verification & validation | 9 | Keep |
| Data dictionary & tickers | 2 | Keep |
| Bootstrap | 1 | Keep |
| Superseded validators | 5 | Archived |
| One-off debug/diagnostic | 9 | Archived |
| Code-mod patches (non-executable) | 7 | Archived |
| One-off runners | 2 | Archived |
| One-off migration | 1 | Archived |
| Profiler | 1 | Archived |
| Experiments (R&D) | 5 | Archived |
| Redundant validation subfolder | 12 | Archived |

**Active scripts** (in `scripts/`):
```
atualizar_dados.ps1        atualizar_todos.py         batch_completo.py
restaurar_historico.py     setup_db.py                setup_companies_table.py
patch_database_sectors_v2.py  gerar_base_analitica.py  calc_financial_kpis.py
final_verification.py      quick_verify.py            verify_consolidation.py
verify_line_id_base.py     smoke_validate.py          build_canonical_dict.py
expand_tickers.py          bootstrap_windows.ps1
```

**Active validation scripts** (in `scripts/validation/`):
```
final_verification.py      diagnose_missing_quarters.py
verify_dfc_standalone.py   verify_trimestral.py
```

All archived scripts moved to `archive/` (top-level, outside `scripts/` to avoid `compileall` failures from snippet-only experiment files).

---

### Dashboard

At the time of this audit, the dashboard was a much larger surface. That description is intentionally stale now.

The later repo state reduced the live dashboard to 3 tabs and moved the canonical description into `README.md`, `docs/CONTEXT.md`, and `docs/AGENTS.md`.

---

### Tests

| Metric | Value |
|---|---|
| Test files | 10 |
| Test functions | 116 |
| Stubs/incomplete | 0 |
| Missing module dependencies | 0 |
| Last confirmed passing | 2026-04-01 (`pytest -q` → 116 passed) |

Test files are healthy — no action needed beyond adding `pytest.ini`.

---

### Documentation (before cleanup)

| File | Lines | Issues Found |
|---|---|---|
| `MEMORIADASIA.md` | 754 | Too large; mixes handoff log with current state |
| `CONTEXT.md` | 263 | Section 14 (stabilization patch notes) belongs in session log |
| `COMO_RODAR.md` | 490 | Stale tab names; Task Scheduler section implies pre-configured; `--cvm/--anos` flags in step 7 |
| `docs/ARCHITECTURE_DATA_FLOW.md` | 112 | Current and accurate — no changes needed |

**Stale references fixed in COMO_RODAR.md:**
- Tab list updated to match actual 9 tabs in `app.py`
- Task Scheduler section now includes setup commands
- Step 7 corrected: `--companies`/`--start_year`/`--end_year` (not `--cvm`/`--anos`)

---

## Action Checklist

- [x] Created `AUDIT.md`
- [x] Created `archive/` (top-level) and moved 41 dead scripts
- [x] Archived `dashboard/chart_registry.py` (unused, 972 lines)
- [x] Archived `dashboard/data/data_loader.py` (legacy, superseded)
- [x] Moved full `MEMORIADASIA.md` session history → `docs/SESSIONS.md`
- [x] Rewrote root `MEMORIADASIA.md` as lean current-state summary
- [x] Updated `CONTEXT.md`: removed stale patch-notes section, updated roadmap
- [x] Updated `COMO_RODAR.md`: fixed tab names, Task Scheduler setup, corrected flags
- [x] Created `pytest.ini`
- [x] Archived `cvm_desktop_app.py` and `cvm_updater.py` (legacy redirect wrappers)
- [x] Deleted `tests/test_legacy_wrappers.py` (tested the now-archived wrappers)
- [x] `skills/` kept at root (future design skill foundation)
- [x] Verified: `pytest tests/ -v` → 113 passed
- [x] Verified: `python scripts/smoke_validate.py` → OK
- [x] Verified: `python scripts/batch_completo.py --help` → flags match docs

---

## Later Drift Notes

- The active dashboard is now read-only and has 3 tabs: `Visao Geral`, `Demonstrações`, `Download`.
- `cvm_pyqt_app.py` became the operational updater and the main write path.
- The documentation truth moved to `README.md`, `docs/CONTEXT.md`, `docs/AGENTS.md`, and `COMO_RODAR.md`.
- The audit's test counts and dashboard tab counts should not be treated as current.
