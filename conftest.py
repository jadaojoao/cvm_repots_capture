import sys
from pathlib import Path

# Garante que o diretório raiz do projeto esteja no sys.path,
# necessário para importar cvm_pyqt_app e outros módulos raiz nos testes.
sys.path.insert(0, str(Path(__file__).resolve().parent))
