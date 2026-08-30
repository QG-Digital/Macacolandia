#!/usr/bin/env python3
"""Publica o Macacolandia no GitHub e prepara o instalador Windows quando possível.

Uso:
  python publicar_macacolandia.py
  python publicar_macacolandia.py --skip-build
  python publicar_macacolandia.py --repo QG-Digital/Macacolandia
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_REPO = "QG-Digital/Macacolandia"


def run(command: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"[publicar] $ {' '.join(command)}")
    return subprocess.run(command, cwd=cwd or ROOT, text=True, check=check)


def build_app(skip: bool) -> None:
    if skip:
        print("[publicar] Compilação ignorada por solicitação.")
        return
    result = run([sys.executable, str(ROOT / "compilador.py")], check=False)
    if result.returncode:
        raise SystemExit("A compilação do Macacolandia falhou.")


def build_installer() -> None:
    makensis = shutil.which("makensis")
    script = ROOT / "installer.nsi"
    if not makensis or not script.exists():
        print("[publicar] NSIS não encontrado; instalador será pulado. No Windows, instale NSIS e execute novamente.")
        return
    result = run([makensis, str(script)], check=False)
    if result.returncode:
        raise SystemExit("A criação do instalador NSIS falhou.")


def publish(repo: str, skip_build: bool) -> None:
    build_app(skip_build)
    build_installer()
    gh = shutil.which("gh")
    git = shutil.which("git")
    if not gh or not git:
        raise SystemExit("É necessário ter Git e GitHub CLI instalados e autenticados.")

    with tempfile.TemporaryDirectory(prefix="macacolandia-publish-") as temp:
        checkout = Path(temp) / "Macacolandia"
        clone = run([gh, "repo", "clone", repo, str(checkout)], check=False)
        if clone.returncode:
            raise SystemExit(f"Não foi possível clonar {repo}. Confirme gh auth login e o acesso ao repositório.")
        for item in ROOT.iterdir():
            if item.name in {".git", "dist", "build", "__pycache__"}:
                continue
            destination = checkout / item.name
            if item.is_dir():
                shutil.copytree(item, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(item, destination)
        run([git, "add", "-A"], cwd=checkout)
        status = subprocess.run([git, "status", "--porcelain"], cwd=checkout, text=True, capture_output=True, check=True)
        if not status.stdout.strip():
            print("[publicar] Nenhuma alteração nova para enviar.")
            return
        run([git, "-c", "user.name=QG-Digital", "-c", "user.email=qg-digital@users.noreply.github.com", "commit", "-m", "Atualiza Macacolandia"], cwd=checkout)
        run([git, "push", "origin", "HEAD"], cwd=checkout)
    print(f"[publicar] Macacolandia publicado em https://github.com/{repo}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila e publica o Macacolandia no GitHub.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"Repositório GitHub (padrão: {DEFAULT_REPO})")
    parser.add_argument("--skip-build", action="store_true", help="Não executar compilador.py")
    args = parser.parse_args()
    publish(args.repo, args.skip_build)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
