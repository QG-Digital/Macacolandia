#!/usr/bin/env python3
"""Compila somente o Macacolandia em um executável com PyInstaller."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "dist"
NAME = "Macacolandia"


def main() -> int:
    pyinstaller = shutil.which("pyinstaller")
    if not pyinstaller:
        print("PyInstaller não encontrado. Instale com: pip install pyinstaller")
        return 1
    required = [ROOT / "backend.py", ROOT / "index.html", ROOT / "desktop.js", ROOT / "desktop.css"]
    missing = [str(path.name) for path in required if not path.exists()]
    if missing:
        print("Arquivos obrigatórios ausentes: " + ", ".join(missing))
        return 1
    separator = ";" if sys.platform.startswith("win") else ":"
    command = [
        pyinstaller, "--noconfirm", "--clean", "--windowed", "--name", NAME,
        "--add-data", f"{ROOT / 'index.html'}{separator}.",
        "--add-data", f"{ROOT / 'desktop.js'}{separator}.",
        "--add-data", f"{ROOT / 'desktop.css'}{separator}.",
        str(ROOT / "backend.py"),
    ]
    print("Compilando somente o Macacolandia…")
    print(" ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode == 0:
        print(f"Executável criado em: {OUTPUT / NAME}")
    else:
        print("A compilação terminou com erro.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
