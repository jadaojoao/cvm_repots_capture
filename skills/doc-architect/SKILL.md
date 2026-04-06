---
name: doc-architect
description: >
  Reorganize, write, maintain, and sync documentation for technical Python
  projects (scrapers, dashboards, data pipelines). Use this skill whenever the
  user wants to clean up root-level clutter, decide what belongs at root vs
  docs/, write or rewrite README/CONTEXT/COMO_RODAR/MEMORIADASIA files,
  restructure reference docs, co-author any project documentation, or update
  docs after a code change. Trigger on: "clean up docs", "rewrite README",
  "where should this file go", "too many .md files", "reorganize documentation",
  "write a CONTEXT", "help me document this", "update the docs after my change",
  "what docs need updating", "keep docs in sync".
---

# Doc Architect

Merges two workflows: **co-authoring** (gather context → build section by section → reader-test) and **documentation templates** (opinionated structure for each doc type). Focused on technical Python projects.

---

## When to Use Each Mode

| Situation | Mode |
|---|---|
| Root has too many .md files | → **Reorganize** |
| Need to write or rewrite a specific doc | → **Co-author** |
| Not sure what a file should contain | → **Template** |
| Code just changed — what docs need updating? | → **Sync** |
| Full project doc overhaul | → All four, in sequence |

---

## Mode 1 — Reorganize (Root Cleanup)

**Goal:** decide what lives at root vs `docs/` vs `archive/`.

### Root — keep only these
- `README.md` — first thing anyone reads after cloning
- `CLAUDE.md` — Claude Code reads this from root (required)
- `COMO_RODAR.md` — user tutorial, stays discoverable
- `requirements.txt`, `pytest.ini`, `main.py`, entry-point `.py` files

### Move to `docs/`
- `CONTEXT.md` — architecture reference, relevant when reading code
- `MEMORIADASIA.md` — agent handoff notes
- `AUDIT.md` — audit/cleanup records
- `.pdf` reference documents (specs, regulatory docs)
- `ARCHITECTURE_*.md`, `SESSIONS.md`

### Move to `archive/`
- Legacy wrappers, deprecated scripts, one-off debug files
- Old versions of docs that have been superseded

### After moving: update cross-references
Search for paths to moved files in `CLAUDE.md`, `README.md`, and any other docs that link to them. Update paths to `docs/FILENAME`.

---

## Mode 2 — Co-Author a Document

Three stages. Allow the user to skip or compress any stage.

### Stage 1: Context
Ask:
1. Who reads this? (developer, new contributor, AI agent, end user)
2. What decision or action should they be able to take after reading?
3. What do you already have? (paste notes, old version, bullet points)

Then ask targeted gap-filling questions. Don't ask more than 3-4 at once.

### Stage 2: Build Section by Section
For each section:
- Draft it
- Ask: "Does this match what you meant, or should we adjust X?"
- Offer 2-3 alternative phrasings if the first draft misses the tone
- Use the templates below as the skeleton

Keep it iterative. Don't dump a full draft and ask "is this ok?" — build it collaboratively.

### Stage 3: Reader Test
Before finalizing, mentally simulate a reader who has never seen the project:
- Can they answer "what does this project do?" in 10 seconds?
- Can they run it with only what's written?
- Are there any undefined terms or assumed knowledge?

Flag gaps. Offer fixes.

---

## Mode 3 — Templates

### README.md (root)
```markdown
# [Project Name]

One-sentence description of what it does and who it's for.

## Quick Start
\`\`\`bash
# minimum steps to get something running
\`\`\`

## What It Does
2-3 sentences. Focus on output, not implementation.

## Architecture
Brief description + link to docs/CONTEXT.md for depth.

## Interfaces
List the official entry points (CLI, GUI, dashboard URL).

## Data
Where data lives, what format, rough size.
```

### CONTEXT.md (→ docs/)
```markdown
# CONTEXT.md — Technical Architecture

## What This Project Is
[1-paragraph executive summary]

## Pipeline
[Source] → [Processing step] → [Storage] → [Visualization]

## Key Design Decisions
- Why SQLite (not PostgreSQL) locally
- Why Streamlit (not Dash)
- Any non-obvious choices

## Business Rules
[Validation rules, data integrity constraints, QA criteria]

## Critical Conventions
[Gotchas: int(year), lo() helper, etc. — things that bite people]

## Current State
[Date] — [what works, what's pending, what's known broken]

## Roadmap
[Completed priorities] → [Next priorities]
```

### COMO_RODAR.md (root — user-facing tutorial)
```markdown
# Como Rodar

## Pré-requisitos
[Python version, OS, any external deps]

## Instalação
\`\`\`bash
[step by step]
\`\`\`

## Rodando o Dashboard
\`\`\`bash
[exact command]
\`\`\`

## O que tem em cada aba
[One paragraph per tab — what it shows, how to use it]

## Atualizando os dados
[Options A, B, C — from easiest to most powerful]

## Adicionando uma nova empresa
[Exact steps]

## Problemas comuns
| Sintoma | Solução |
|---|---|
```

### MEMORIADASIA.md (→ docs/, lean version)
```markdown
# MEMORIADASIA.md — Estado Atual

> Resumo lean. Histórico completo em docs/SESSIONS.md.

## Última Sessão
[Sessão N — Agente — Data]
[Bullet list of what was done + validation results]

## Estado Atual do Sistema
[Dashboard tabs, DB stats, key entry points]

## Decisões Técnicas Não-Óbvias
| Feature | Detalhe |
|---|---|

## Problemas Abertos
[Bullet list]

## Arquivos Legados
[What exists but shouldn't be touched]
```

### AUDIT.md (→ docs/)
```markdown
# AUDIT.md — [Date]

## Findings Summary
[Tables: scripts active/archived, dashboard status, test counts, doc issues]

## Action Checklist
- [ ] item
- [x] completed item
```

---

## Mode 4 — Sync (Code → Docs)

**Goal:** after a code change, find every doc that needs updating and update it.

### Step 1: Identify what changed
Ask the user (or read from `git diff --stat HEAD`):
- Which files were added, modified, or deleted?
- What did the change do? (new feature, rename, removal, config change)

### Step 2: Map changes to docs using this table

| What changed | Docs to update |
|---|---|
| `dashboard/tabs/` — new or renamed tab | `COMO_RODAR.md` tab descriptions · `MEMORIADASIA.md` state · `CONTEXT.md` Estado Atual |
| `dashboard/app.py` — tab list or sidebar | `COMO_RODAR.md` tab names |
| `scripts/` — new active script | `README.md` workflow · `CLAUDE.md` Scripts Structure |
| `scripts/` — script archived or deleted | `AUDIT.md` · `CLAUDE.md` |
| `src/scraper.py` or `src/database.py` | `CONTEXT.md` Pipeline/Architecture |
| New entry point (`.py` at root) | `README.md` Interfaces section |
| `requirements.txt` changed | `CONTEXT.md` Stack Técnica |
| `tests/` — new test file or count changed | `MEMORIADASIA.md` state block |
| DB schema changed | `CONTEXT.md` Database section · `CLAUDE.md` |
| New KPI or indicator | `COMO_RODAR.md` tab description for Indicadores |
| Company/ticker count changed | `MEMORIADASIA.md` · `COMO_RODAR.md` Screener section |

### Step 3: For each affected doc
1. Read the current section
2. Draft the minimal update (don't rewrite sections that are still accurate)
3. Confirm with user before writing

### Step 4: Validation checklist
Before finishing, verify:
- [ ] No doc still references a file/feature that no longer exists
- [ ] Tab names in `COMO_RODAR.md` match actual tab labels in `dashboard/app.py`
- [ ] Script names in `README.md` exist in `scripts/`
- [ ] Company/year counts are current
- [ ] `CLAUDE.md` Scripts Structure section matches `scripts/` directory

---

## Reference: File Placement Decision Tree

```
Is it the first thing a new person reads after cloning?
  Yes → root
  No ↓

Is it required by a tool at a fixed path? (pytest.ini, CLAUDE.md)
  Yes → root
  No ↓

Is it a user-facing tutorial or quickstart?
  Yes → root (COMO_RODAR.md)
  No ↓

Is it a reference doc, architecture note, or audit record?
  Yes → docs/
  No ↓

Is it a deprecated/one-off/superseded file?
  Yes → archive/
```
