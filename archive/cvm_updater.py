# -*- coding: utf-8 -*-
"""
Legacy wrapper: redireciona para a interface oficial PyQt6.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _build_redirect_command() -> tuple[list[str], str]:
    root = Path(__file__).resolve().parent
    target = root / "cvm_pyqt_app.py"
    return [sys.executable, str(target)], str(root)


def main() -> int:
    print(
        "[DEPRECATED] cvm_updater.py esta em modo legado. "
        "Redirecionando para 'python cvm_pyqt_app.py'."
    )
    cmd, cwd = _build_redirect_command()
    try:
        return subprocess.call(cmd, cwd=cwd)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
