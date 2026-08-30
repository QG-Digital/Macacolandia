import base64
import json
import mimetypes
import os
import platform
import shutil
import string
import threading
import uuid
import urllib.parse
import webbrowser
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import webview
except ImportError:  # permite testar o scanner antes de instalar a dependência visual
    webview = None


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} EB"


def stat_size(path: str) -> int:
    try:
        return os.stat(path, follow_symlinks=False).st_size
    except (OSError, PermissionError, FileNotFoundError):
        return 0


def folder_size(path: str) -> int:
    """Calcula o tamanho sem recursão Python, evitando estouro em árvores profundas."""
    total = 0
    try:
        for current, dirs, files in os.walk(path, topdown=True, followlinks=False):
            dirs[:] = [directory for directory in dirs if not os.path.islink(os.path.join(current, directory))]
            for filename in files:
                total += stat_size(os.path.join(current, filename))
    except (OSError, PermissionError, FileNotFoundError):
        pass
    return total


def file_kind(name: str) -> tuple[str, str, bool]:
    mime, _ = mimetypes.guess_type(name)
    mime = mime or "application/octet-stream"
    if mime.startswith("video/"):
        return "vídeo", mime, True
    if mime.startswith("image/"):
        return "imagem", mime, True
    if mime.startswith("audio/"):
        return "áudio", mime, True
    if mime.startswith("text/") or mime in {"application/pdf", "application/zip", "application/json"}:
        return "documento", mime, False
    return "outro", mime, False


TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".json", ".json5", ".js", ".jsx", ".ts", ".tsx",
    ".html", ".htm", ".css", ".scss", ".less", ".py", ".pyw", ".toml", ".yaml",
    ".yml", ".ini", ".cfg", ".conf", ".properties", ".env", ".xml", ".csv", ".sql",
    ".sh", ".bash", ".bat", ".cmd", ".ps1", ".java", ".c", ".h", ".cpp", ".hpp",
    ".rs", ".go", ".php", ".rb", ".swift", ".kt", ".log", ".gitignore"
}


def image_thumbnail_src(path: str, mime: str) -> str | None:
    """Retorna o caminho local da imagem sem bloquear a varredura lendo seu conteúdo."""
    try:
        return Path(path).resolve().as_uri()
    except (OSError, ValueError):
        return None


def risk_for_file(name: str) -> tuple[bool, str]:
    extension = Path(name).suffix.lower()
    risky = {".exe", ".scr", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jar", ".msi", ".com", ".hta"}
    if extension in risky:
        return True, f"Extensão executável ou script: {extension}"
    return False, ""


def scan_level(path: str) -> dict[str, Any]:
    """Retorna apenas os filhos diretos; o peso das subpastas é calculado sem abrir seus filhos."""
    children = []
    error = None
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if entry.is_symlink():
                        continue
                    is_folder = entry.is_dir(follow_symlinks=False)
                    size = folder_size(entry.path) if is_folder else stat_size(entry.path)
                    kind, mime, previewable = file_kind(entry.name)
                    possible_risk, risk_reason = (False, "") if is_folder else risk_for_file(entry.name)
                    children.append({
                        "name": entry.name,
                        "path": entry.path,
                        "type": "folder" if is_folder else "file",
                        "size_bytes": size,
                        "size": format_bytes(size),
                        "kind": "pasta" if is_folder else kind,
                        "mime": None if is_folder else mime,
                        "previewable": False if is_folder else previewable,
                        "thumbnail_src": None if is_folder or kind != "imagem" else image_thumbnail_src(entry.path, mime),
                        "possible_risk": possible_risk,
                        "risk_reason": risk_reason,
                        "children": None if is_folder else [],
                        "loaded": False if is_folder else True,
                    })
                except (OSError, PermissionError, FileNotFoundError):
                    continue
    except (OSError, PermissionError, FileNotFoundError) as exc:
        error = f"Acesso negado ou pasta indisponível: {exc.__class__.__name__}"
    children.sort(key=lambda item: item["size_bytes"], reverse=True)
    return {"path": path, "children": children, "error": error}


class TreeSizeAPI:
    def __init__(self):
        self.window = None
        self.jobs: dict[str, dict[str, Any]] = {}
        self.jobs_lock = threading.Lock()
        self._reserved_file = Path.home() / ".macacolandia_reservas.json"

    def set_window(self, window):
        self.window = window

    def load_reserved(self):
        try:
            if not self._reserved_file.exists():
                return {"ok": True, "items": []}
            with self._reserved_file.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            items = payload if isinstance(payload, list) else payload.get("items", [])
            return {"ok": True, "items": [item for item in items if isinstance(item, dict) and item.get("path")]}
        except (OSError, json.JSONDecodeError) as exc:
            return {"ok": False, "items": [], "error": f"Não consegui carregar as reservas: {exc}"}

    def save_reserved(self, items):
        try:
            clean_items = [item for item in (items or []) if isinstance(item, dict) and item.get("path")]
            temporary = self._reserved_file.with_suffix(".tmp")
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(clean_items, handle, ensure_ascii=False, indent=2)
            temporary.replace(self._reserved_file)
            return {"ok": True, "path": str(self._reserved_file)}
        except (OSError, TypeError, ValueError) as exc:
            return {"ok": False, "error": f"Não consegui salvar as reservas: {exc}"}

    def create_donation_pix(self, amount):
        try:
            value = round(float(amount), 2)
        except (TypeError, ValueError):
            return {"success": False, "error": "Informe um valor válido para a doação."}
        if value < 1:
            return {"success": False, "error": "A doação mínima é de R$ 1,00."}
        payload = {"transaction_amount": value, "description": "Doacao_Macacolandia", "email": f"doacao_{uuid.uuid4().hex[:8]}@localinsta.com"}
        print(f"[Macacolandia] donation_pix_request amount={value}", flush=True)
        try:
            response = requests.post("https://mercadolivre.qgdigital.workers.dev/gerar", json=payload, timeout=15)
            payment = response.json()
            transaction = ((payment.get("point_of_interaction") or {}).get("transaction_data") or {})
            if 200 <= response.status_code < 300 and payment.get("status") in {"pending", "in_process"} and transaction.get("qr_code_base64") and transaction.get("qr_code"):
                print(f"[Macacolandia] donation_pix_created payment_id={payment.get('id')}", flush=True)
                return {"success": True, "qr_code": transaction["qr_code_base64"], "qr_code_text": transaction["qr_code"], "payment_id": payment.get("id"), "valor": value}
            print(f"[Macacolandia] ERROR donation_pix_response={payment}", flush=True)
            return {"success": False, "error": payment.get("message") or payment.get("error") or "Não foi possível gerar o Pix."}
        except (requests.RequestException, ValueError) as exc:
            print(f"[Macacolandia] ERROR donation_pix={exc!r}", flush=True)
            return {"success": False, "error": "Não foi possível comunicar com o servidor de pagamentos."}

    def create_donation_card(self, payload):
        data = payload or {}
        try:
            value = round(float(data.get("amount")), 2)
        except (TypeError, ValueError):
            return {"success": False, "error": "Informe um valor válido para a doação."}
        token = str(data.get("token") or "").strip()
        payment_method_id = str(data.get("payment_method_id") or "").strip()
        payer = data.get("payer") or {}
        email = str(payer.get("email") or "").strip()
        identification = payer.get("identification") or {}
        cpf = str(identification.get("number") or "").strip()
        if value < 1 or not token or not payment_method_id or not email or not cpf:
            return {"success": False, "error": "Valor, token seguro, método, e-mail e CPF são obrigatórios."}
        worker_payload = {"token": token, "issuer_id": data.get("issuer_id"), "payment_method_id": payment_method_id, "transaction_amount": value, "installments": 1, "description": "Doacao_Macacolandia_Cartao", "payer": {"email": email, "identification": {"type": identification.get("type") or "CPF", "number": cpf}}}
        print(f"[Macacolandia] donation_card_request amount={value} payment_method={payment_method_id!r}", flush=True)
        try:
            response = requests.post("https://mercadolivre.qgdigital.workers.dev/cartao", json=worker_payload, timeout=30)
            payment = response.json()
            if response.status_code in (200, 201) and payment.get("id"):
                print(f"[Macacolandia] donation_card_created payment_id={payment.get('id')}", flush=True)
                return {"success": True, "payment_id": payment.get("id"), "status": payment.get("status"), "valor": value}
            print(f"[Macacolandia] ERROR donation_card_response={payment}", flush=True)
            return {"success": False, "error": payment.get("message") or payment.get("error") or "O cartão não foi aprovado."}
        except (requests.RequestException, ValueError) as exc:
            print(f"[Macacolandia] ERROR donation_card={exc!r}", flush=True)
            return {"success": False, "error": "Não foi possível comunicar com o servidor de pagamentos."}

    def list_drives(self):
        system = platform.system()
        if system == "Windows":
            drives = [f"{letter}:/" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:/")]
        elif system == "Darwin":
            volumes = Path("/Volumes")
            drives = ["/"] + ([str(p) for p in volumes.iterdir() if p.is_dir()] if volumes.exists() else [])
        else:
            drives = ["/"]
            for base in ("/media", "/mnt", "/run/media"):
                root = Path(base)
                if root.exists():
                    drives.extend(str(p) for p in root.iterdir() if p.is_dir())
        return sorted(set(drives))

    def start_drive_scan(self):
        job_id = uuid.uuid4().hex
        with self.jobs_lock:
            self.jobs[job_id] = {"status": "queued", "kind": "drives", "path": "", "result": None, "error": None}
        threading.Thread(target=self._run_drive_job, args=(job_id,), daemon=True).start()
        return {"job_id": job_id}

    def _run_drive_job(self, job_id: str):
        with self.jobs_lock:
            self.jobs[job_id]["status"] = "running"
        try:
            result = self.list_drives()
            with self.jobs_lock:
                self.jobs[job_id]["status"] = "done"
                self.jobs[job_id]["result"] = result
        except Exception as exc:
            with self.jobs_lock:
                self.jobs[job_id]["status"] = "error"
                self.jobs[job_id]["error"] = str(exc)

    def get_disk_info(self, path):
        try:
            total, used, free = shutil.disk_usage(path)
            used_percent = round((used / total) * 100, 1) if total else 0
            if used_percent >= 90:
                bananas, status = "🍌🍌🍌🍌🍌", "Cheio demais"
            elif used_percent >= 75:
                bananas, status = "🍌🍌🍌🍌◌", "Ficando apertado"
            elif used_percent >= 50:
                bananas, status = "🍌🍌🍌◌◌", "Tá meio cheio"
            else:
                bananas, status = "🍌🍌◌◌◌", "Tranquilo"
            return {"path": path, "total_bytes": total, "used_bytes": used, "free_bytes": free, "total": format_bytes(total), "used": format_bytes(used), "free": format_bytes(free), "used_percent": used_percent, "bananas": bananas, "status": status}
        except (OSError, PermissionError) as exc:
            return {"error": f"Não consegui medir este HD: {exc}"}

    def open_github_search(self, filename):
        query = urllib.parse.quote(str(filename))
        url = f"https://github.com/search?q={query}&type=code"
        try:
            webbrowser.open(url)
            return {"ok": True, "url": url, "message": "Busca aberta no GitHub. Isso é só referência, não é antivírus."}
        except Exception as exc:
            return {"ok": False, "url": url, "error": str(exc)}

    def select_folder(self):
        if not self.window:
            return None
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None

    def _new_job(self, kind: str, path: str) -> str:
        job_id = uuid.uuid4().hex
        with self.jobs_lock:
            self.jobs[job_id] = {"status": "queued", "kind": kind, "path": path, "result": None, "error": None}
        threading.Thread(target=self._run_job, args=(job_id,), daemon=True).start()
        return job_id

    def _run_job(self, job_id: str):
        with self.jobs_lock:
            job = self.jobs[job_id]
            job["status"] = "running"
        try:
            result = scan_level(job["path"])
            with self.jobs_lock:
                job["status"] = "done"
                job["result"] = result
        except Exception as exc:  # mantém o worker vivo mesmo em discos problemáticos
            with self.jobs_lock:
                job["status"] = "error"
                job["error"] = str(exc)

    def start_scan(self, path):
        if not path or not os.path.isdir(path):
            return {"error": "Caminho inválido ou inacessível."}
        return {"job_id": self._new_job("root", path)}

    def expand_folder(self, path):
        if not path or not os.path.isdir(path):
            return {"error": "Pasta inválida ou inacessível."}
        return {"job_id": self._new_job("children", path)}

    def get_job(self, job_id):
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if not job:
                return {"status": "error", "error": "Análise não encontrada."}
            return {"status": job["status"], "result": job["result"], "error": job["error"]}

    def select_destination(self):
        if not self.window:
            return None
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None

    def create_folder(self, parent, name):
        """Cria uma pasta dentro do diretório escolhido pelo usuário."""
        print(f"[Macacolandia] create_folder parent={parent!r} name={name!r}", flush=True)
        if not parent or not os.path.isdir(parent):
            return {"ok": False, "error": "A pasta de destino é inválida ou inacessível."}
        clean_name = str(name or "").strip()
        if not clean_name or clean_name in {".", ".."} or "/" in clean_name or chr(92) in clean_name:
            return {"ok": False, "error": "Use um nome de pasta válido, sem caminhos adicionais."}
        target = os.path.join(parent, clean_name)
        try:
            os.makedirs(target, exist_ok=False)
            print(f"[Macacolandia] folder_created path={target!r}", flush=True)
            return {"ok": True, "path": target}
        except FileExistsError:
            print(f"[Macacolandia] ERROR folder_exists path={target!r}", flush=True)
            return {"ok": False, "error": "Já existe uma pasta com esse nome."}
        except (OSError, PermissionError) as exc:
            print(f"[Macacolandia] ERROR folder_create_failed error={exc!r}", flush=True)
            return {"ok": False, "error": f"Não foi possível criar a pasta: {exc}"}

    def start_operation(self, operation, paths, destination=None):
        print(f"[Macacolandia] start_operation operation={operation!r} paths={paths!r} destination={destination!r}", flush=True)
        if operation not in {"move", "delete"} or not paths:
            return {"error": "Nada foi selecionado."}
        if operation == "move" and (not destination or not os.path.isdir(destination)):
            return {"error": "Escolha uma pasta de destino válida."}
        job_id = uuid.uuid4().hex
        with self.jobs_lock:
            self.jobs[job_id] = {"status": "queued", "kind": "operation", "operation": operation, "paths": paths, "destination": destination, "progress": 0, "result": None, "error": None}
        threading.Thread(target=self._run_operation, args=(job_id,), daemon=True).start()
        return {"job_id": job_id}

    def _run_operation(self, job_id):
        with self.jobs_lock:
            job = self.jobs[job_id]
            job["status"] = "running"
        results = []
        paths = job["paths"]
        for index, source in enumerate(paths, start=1):
            item = {"path": source, "ok": False}
            try:
                if job["operation"] == "move":
                    target = os.path.join(job["destination"], os.path.basename(os.path.normpath(source)))
                    if os.path.abspath(source) != os.path.abspath(target):
                        shutil.move(source, target)
                    item["destination"] = target
                else:
                    if os.path.isdir(source) and not os.path.islink(source):
                        shutil.rmtree(source)
                    else:
                        os.remove(source)
                item["ok"] = True
            except (OSError, PermissionError, FileNotFoundError) as exc:
                item["error"] = str(exc)
            results.append(item)
            print(f"[Macacolandia] operation_item path={source!r} ok={item['ok']} error={item.get('error')!r}", flush=True)
            with self.jobs_lock:
                job["progress"] = round(index / len(paths) * 100)
        with self.jobs_lock:
            job["status"] = "done"
            job["result"] = {"items": results, "ok": sum(1 for item in results if item["ok"]), "failed": sum(1 for item in results if not item["ok"])}

    def get_preview(self, path):
        if not path or not os.path.isfile(path):
            return {"ok": False, "error": "Arquivo não encontrado."}
        suffix = Path(path).suffix.lower()
        if suffix in TEXT_EXTENSIONS or Path(path).name.lower() in {"dockerfile", "makefile", "license", "readme"}:
            try:
                size = os.path.getsize(path)
                if size > 2 * 1024 * 1024:
                    return {"ok": False, "kind": "texto", "error": "Este arquivo é maior que 2 MB e não será carregado na prévia."}
                with open(path, "r", encoding="utf-8", errors="replace") as text_file:
                    return {"ok": True, "kind": "texto", "mime": "text/plain", "text": text_file.read()}
            except (OSError, PermissionError) as exc:
                return {"ok": False, "kind": "texto", "error": f"Não consegui ler este arquivo: {exc}"}
        kind, mime, previewable = file_kind(path)
        if not previewable:
            return {"ok": False, "error": "Este tipo de arquivo não tem prévia dentro do app.", "kind": kind}
        try:
            size = os.path.getsize(path)
            if kind == "imagem" and size <= 12 * 1024 * 1024:
                with open(path, "rb") as media:
                    encoded = base64.b64encode(media.read()).decode("ascii")
                return {"ok": True, "kind": kind, "mime": mime, "src": f"data:{mime};base64,{encoded}"}
            return {"ok": True, "kind": kind, "mime": mime, "src": Path(path).resolve().as_uri(), "limited": kind == "imagem"}
        except (OSError, PermissionError) as exc:
            return {"ok": False, "error": f"Não consegui abrir este arquivo: {exc}"}

    def export_json(self, payload, target_path=None):
        if not target_path and self.window:
            desktop = Path.home() / "Desktop"
            result = self.window.create_file_dialog(webview.SAVE_DIALOG, directory=str(desktop if desktop.is_dir() else Path.home()), save_filename="macacolandia-para-ia.txt", file_types=("Text files (*.txt)", "All files (*.*)"))
            target_path = result[0] if result else None
        if not target_path:
            return {"ok": False, "error": "Exportação cancelada."}
        try:
            with open(target_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            return {"ok": True, "path": target_path}
        except OSError as exc:
            return {"ok": False, "error": str(exc)}


def start():
    if webview is None:
        raise SystemExit("Dependência ausente: execute 'pip install -r requirements.txt' antes de iniciar.")
    api = TreeSizeAPI()
    window = webview.create_window("TreeSize Desktop", url=str(Path(__file__).with_name("index.html")), js_api=api, width=1240, height=820, min_size=(920, 620))
    api.set_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    start()
