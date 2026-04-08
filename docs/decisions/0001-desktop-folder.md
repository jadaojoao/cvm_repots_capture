# 0001 — Mover App Desktop para pasta `desktop/`

- **Status:** accepted
- **Data:** 2026-04-07
- **Autor:** human+ai

## Contexto

O arquivo `cvm_pyqt_app.py` (~125 KB, ~3.000 linhas) residia na raiz do repositório.
O projeto entra em uma nova fase de crescimento (possível deploy cloud, mais features, colaboração).
Arquivos de aplicação grandes na raiz dificultam navegação e onboarding de agentes de IA.

## Decisão

Movemos `cvm_pyqt_app.py` para `desktop/cvm_pyqt_app.py` e criamos `desktop/__init__.py`
para tornar o diretório um pacote Python importável.

Todos os imports (`from cvm_pyqt_app import ...`) foram atualizados para
`from desktop.cvm_pyqt_app import ...` nos testes. O `conftest.py` não precisou de alteração
pois já insere o root do projeto no `sys.path`.

## Alternativas Consideradas

- **Manter na raiz:** Funcional, mas dificulta escala — qualquer split futuro do monolito
  exigiria mover novamente com mais impacto.
- **Split do monolito em módulos `desktop/`:** Alto risco agora, app estável — adiado para
  sessão futura quando houver motivação funcional clara.

## Consequências

- Comando de execução muda: `python cvm_pyqt_app.py` → `python desktop/cvm_pyqt_app.py`
- A raiz fica mais limpa (apenas `main.py` e `conftest.py` como `.py` na raiz)
- Futuros splits do monolito ocorrem naturalmente dentro de `desktop/`
- O Task Scheduler (`CVM_Atualizar_Dados`) executa `atualizar_todos.py`, não `cvm_pyqt_app.py` diretamente — não impactado

## Referências

- `.ai-activity.log` — log de todas as mudanças aplicadas nesta sessão
