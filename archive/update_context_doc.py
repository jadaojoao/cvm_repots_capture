# -*- coding: utf-8 -*-
import os

path = r'c:\Users\jadaojoao\Documents\cvm_repots_capture\CONTEXT.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Update Executive Summary
old_exec = """- **Objetivo final:** gerar uma base histórica confiável e um Dashboard Analítico (Terminal Financeiro) para análise fundamentalista rápida.
- **Escopo atual:** Prioridades 1 a 7 concluídas ou em fase final (Integridade, QA, Padronização, Bancos, Análise/KPIs, Dashboard e Automação SQLite).
- **Estado atual:** O projeto agora possui um **Terminal CVM Analytics** alimentado por SQLite com dados 2022-2025 e comparação de peers."""

new_exec = """- **Objetivo final:** Gerar uma base histórica confiável de alta performance e um Terminal Financeiro de nível profissional.
- **Escopo atual:** Desenvolvimento de interfaces nativas (Desktop GUI e TUI) de alto desempenho para fugir do "overhead" de navegadores e processos pesados.
- **Estado atual:** O projeto agora possui um **Motor Vetorizado & Paralelo** com sincronização para SQLite (WAL mode). Conta com um app Desktop nativo (`customtkinter`) e um Terminal TUI (`rich`) para atualizações locais."""

content = content.replace(old_exec, new_exec)

# Update Priority 7 and 8
old_p7 = """**Prioridade 7: Expansão em Massa (Automação SQLite)**
Orquestrar a ferramenta para ler as Top 100 ações da B3 de uma vez, salvando todo o conteúdo histórico validado em um banco de dados relacional flexível (SQLite/PostgreSQL) para viabilizar queries SQL pesadas."""

new_p7 = """**Prioridade 7 (concluída): Expansão em Massa (Automação SQLite)**
Orquestrar a ferramenta para ler as Top 100 ações da B3 de uma vez, salvando todo o conteúdo histórico validado em um banco de dados relacional flexível (SQLite/PostgreSQL) para viabilizar queries SQL pesadas. Implementadas interfaces Desktop e TUI para controle granular dessa expansão sem instabilidade do sistema.

**Prioridade 8 (concluída): Otimização de Performance Extrema**
Reconstrução do core do Scraper para usar Vetorização (Pandas Boolean Masks) em vez de loops `apply()`, implementação de downloads paralelos com `ThreadPoolExecutor` e sintonia fina do SQLite com Modo WAL (Write-Ahead Logging)."""

content = content.replace(old_p7, new_p7)

# Update Technical Stack
old_stack = """- **Linguagem:** Python 3.11+
- **Bibliotecas:** `pandas`, `openpyxl`, `requests`"""

new_stack = """- **Linguagem:** Python 3.11+
- **Bibliotecas:** `pandas` (vetorizado), `sqlalchemy` (async-ready), `requests`, `customtkinter` (GUI), `rich` (TUI), `yfinance`"""

content = content.replace(old_stack, new_stack)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("CONTEXT.md updated successfully via script.")
