# REGRAS DO PROJETO (PROJECT RULES)

## 1. Organização de Pastas
Mantenha a árvore de pastas limpa e organizada conforme a estrutura definida:

- **`/` (Raiz)**: Apenas `main.py`, `requirements.txt`, `CONTEXT.md`, `MEMORIADASIA.md` e arquivos de configuração do git/projeto.
- **`src/`**: Código fonte reutilizável (classes, funções, módulos).
- **`scripts/`**: Scripts de execução única, verificação, debug ou tarefas auxiliares.
- **`data/`**:
  - `data/input/`: Scripts buscam dados brutos/processados aqui.
  - `data/output/`: Resultados gerados que são dados para outros processos.
  - Arquivos de referência (dicionários, templates) ficam na raiz de `data/`.
- **`output/`**: Logs e resultados finais para consumo humano.
- **`docs/`**: Documentação do projeto.

## 2. Configuração do Usuário (USER CONFIG)
Todo script que pode ser executado diretamente (`main.py`, scripts em `scripts/`) DEVE ter um bloco de configuração no topo do arquivo, logo após os imports.

**Padrão Exigido:**
```python
import ...

# ==============================================================================
# USER CONFIGURATION
# ==============================================================================
# Diretórios
DEFAULT_DATA_DIR = "..."
DEFAULT_OUTPUT_DIR = "..."

# Parâmetros Editáveis
PARAMETRO_X = 123
IS_DEBUG = True
# ==============================================================================

def main():
    ...
```

Isso facilita a manutenção e evita "números mágicos" ou caminhos hardcoded no meio do código.

## 3. Manutenção
- Ao criar novos scripts, coloque-os em `scripts/` se forem para uso pontual ou `src/` se forem módulos.
- Sempre verifique se os caminhos de importação estão corretos (`sys.path.append` pode ser necessário em scripts auxiliares).
