#!/usr/bin/env python3
"""Compila e publica somente o site e os artefatos finais do Macacolandia."""
from __future__ import annotations

import argparse
import os
import shutil
import string
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_REPO = "QG-Digital/Macacolandia"
PUBLIC_FILES = {"index.html", "style.css", "script.js", "macacolandia-logo.png", "macacolandia-logo.ico"}


def run(command: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"[publicar] $ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=cwd or ROOT, text=True, check=check)


def build_app(skip: bool) -> None:
    if skip:
        print("[publicar] Compilação ignorada; usando dist/Macacolandia.exe existente.")
        return
    compiler = ROOT / "compilador.py"
    result = run([sys.executable, str(compiler)], check=False)
    if result.returncode:
        raise SystemExit("A compilação do Macacolandia falhou.")


def find_nsis() -> str | None:
    """Procura o makensis no PATH, locais comuns e em todos os volumes Windows."""
    found = shutil.which("makensis") or shutil.which("makensis.exe")
    if found:
        return found
    if os.name != "nt":
        return None

    common = [
        Path(os.environ.get("PROGRAMFILES", "")) / "NSIS" / "makensis.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "NSIS" / "Bin" / "makensis.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "NSIS" / "makensis.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "NSIS" / "Bin" / "makensis.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "NSIS" / "Bin" / "makensis.exe",
    ]
    for candidate in common:
        if candidate.is_file():
            return str(candidate)

    for letter in string.ascii_uppercase:
        drive = Path(f"{letter}:\\\\")
        if not drive.exists():
            continue
        try:
            result = subprocess.run(
                ["where", "/r", str(drive), "makensis.exe"],
                text=True,
                capture_output=True,
                timeout=90,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        for line in result.stdout.splitlines():
            candidate = Path(line.strip())
            if candidate.is_file():
                return str(candidate)
    return None


def build_installer() -> Path:
    makensis = find_nsis()
    script = ROOT / "installer.nsi"
    executable = ROOT / "dist" / "Macacolandia.exe"
    installer = ROOT / "dist" / "Macacolandia-Setup.exe"
    if not makensis:
        raise SystemExit("NSIS não encontrado. O publicador procurou no PATH, locais comuns e em todos os HDs.")
    if not executable.is_file():
        raise SystemExit("O EXE não existe em dist/Macacolandia.exe; execute a compilação primeiro.")
    print(f"[publicar] NSIS encontrado em: {makensis}")
    result = run([makensis, str(script)], check=False)
    if result.returncode or not installer.is_file():
        raise SystemExit("A criação do instalador NSIS falhou ou não gerou dist/Macacolandia-Setup.exe.")
    print(f"[publicar] Instalador criado em: {installer}")
    return installer


def collect_artifacts(downloads: Path) -> list[Path]:
    dist = ROOT / "dist"
    artifacts: list[Path] = []
    candidates = [dist / "Macacolandia.exe", dist / "Macacolandia-Setup.exe"]
    for source in candidates:
        if source.is_file():
            target = downloads / source.name
            shutil.copy2(source, target)
            artifacts.append(target)
    legacy_dir = dist / "Macacolandia"
    if legacy_dir.is_dir() and not any(path.suffix.lower() == ".exe" for path in artifacts):
        archive = downloads / "Macacolandia-portable.zip"
        shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=legacy_dir)
        artifacts.append(archive)
    return artifacts


def stage_public_files(stage: Path) -> list[Path]:
    site = ROOT / "site"
    if not site.is_dir():
        raise SystemExit("A pasta site/ não existe.")
    missing = [name for name in PUBLIC_FILES if not (site / name).is_file()]
    if missing:
        raise SystemExit("Arquivos ausentes na landing page: " + ", ".join(missing))
    for name in sorted(PUBLIC_FILES):
        shutil.copy2(site / name, stage / name)

    downloads = stage / "downloads"
    downloads.mkdir()
    artifacts = collect_artifacts(downloads)
    if not artifacts:
        raise SystemExit("Nenhum EXE foi encontrado em dist/. Execute compilador.py primeiro.")
    (stage / "README.md").write_text(
        "# Macacolandia\n\n"
        "Explorador visual para organizar arquivos e pastas do seu HD.\n\n"
        "Abra `index.html` para conhecer o app e entre em `downloads/` para baixar o executável.\n\n"
        "Repositório: https://github.com/QG-Digital/Macacolandia\n",
        encoding="utf-8",
    )
    return artifacts


def clean_checkout(checkout: Path) -> None:
    for item in checkout.iterdir():
        if item.name != ".git":
            shutil.rmtree(item) if item.is_dir() else item.unlink()


def publish(repo: str, skip_build: bool) -> None:
    build_app(skip_build)
    build_installer()
    gh = shutil.which("gh")
    git = shutil.which("git")
    if not gh or not git:
        raise SystemExit("É necessário ter Git e GitHub CLI instalados e autenticados.")

    with tempfile.TemporaryDirectory(prefix="macacolandia-publish-") as temp:
        checkout = Path(temp) / "Macacolandia"
        if run([gh, "repo", "clone", repo, str(checkout)], check=False).returncode:
            raise SystemExit(f"Não foi possível clonar {repo}. Confirme `gh auth login` e o acesso ao repositório.")
        clean_checkout(checkout)
        stage = Path(temp) / "public"
        stage.mkdir()
        artifacts = stage_public_files(stage)
        for item in stage.iterdir():
            destination = checkout / item.name
            shutil.copytree(item, destination) if item.is_dir() else shutil.copy2(item, destination)

        run([git, "add", "-A"], cwd=checkout)
        status = subprocess.run([git, "status", "--porcelain"], cwd=checkout, text=True, capture_output=True, check=True)
        print("[publicar] Conteúdo que será publicado:\n" + (status.stdout or "(sem alterações)"))
        if status.stdout.strip():
            run([git, "-c", "user.name=QG-Digital", "-c", "user.email=qg-digital@users.noreply.github.com", "commit", "-m", "Publica site e artefatos do Macacolandia"], cwd=checkout)
            run([git, "push", "origin", "HEAD"], cwd=checkout)

        tag = "v" + datetime.now().strftime("%Y.%m.%d.%H%M")
        release_files = [str(path.relative_to(stage)) for path in artifacts]
        release = run([gh, "release", "create", tag, *release_files, "--repo", repo, "--title", f"Macacolandia {tag}", "--notes", "Download oficial do Macacolandia."], cwd=stage, check=False)
        if release.returncode:
            raise SystemExit("O site foi enviado, mas a criação da release falhou. Verifique gh auth e permissões do repositório.")
        print(f"[publicar] Release criada: {tag}")
    print(f"[publicar] Site publicado em https://github.com/{repo}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publica somente site, EXE e instalador do Macacolandia.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"Repositório GitHub (padrão: {DEFAULT_REPO})")
    parser.add_argument("--skip-build", action="store_true", help="Usa os artefatos existentes em dist/")
    args = parser.parse_args()
    publish(args.repo, args.skip_build)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
