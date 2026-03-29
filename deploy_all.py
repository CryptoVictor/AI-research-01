"""
GFE Dataset — Vercel Mass Deployer
Faz o deploy de cada site_XXXX como um projeto Vercel independente,
com nome de projeto aleatório e realista.

Uso:
    python3 deploy_all.py
    python3 deploy_all.py --start 1 --end 100   # deploy parcial
    python3 deploy_all.py --resume               # pula sites já deployados
"""

import subprocess
import csv
import time
import random
import argparse
import sys
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

DATASET_DIR  = "./gfe_dataset"
URLS_CSV     = "./deployed_urls.csv"
ERROR_LOG    = "./deploy_errors.log"
DELAY_SEC    = 1.5

# ─── RANDOM NAME POOLS ───────────────────────────────────────────────────────

_PREFIXES = [
    "hub", "portal", "dash", "info", "net", "data", "view", "base",
    "core", "node", "flow", "link", "labs", "desk", "map", "grid",
    "feed", "vault", "gate", "pulse", "edge", "stack", "cloud", "forge",
    "mint", "wave", "sphere", "nexus", "nova", "prime", "peak", "zone",
]

_WORDS = [
    "finance", "health", "invest", "career", "market", "digital", "crypto",
    "defi", "web3", "chain", "token", "saude", "vagas", "noticias", "gov",
    "bolsa", "fundo", "renda", "tech", "dev", "code", "api", "layer",
    "protocol", "wallet", "block", "ledger", "audit", "report", "insight",
    "analytics", "monitor", "track", "scan", "verify", "secure", "open",
    "public", "civic", "social", "media", "press", "daily", "weekly",
]

_SUFFIXES = [
    "app", "io", "co", "hq", "br", "sp", "pro", "dev", "site", "web",
    "online", "digital", "hub", "net", "info", "plus", "go", "now",
]

_USED_NAMES: set[str] = set()


def random_project_name() -> str:
    """Gera um nome de projeto único, ex: 'health-vault-io', 'defi-core-br'."""
    for _ in range(100):
        parts = random.choice([
            lambda: f"{random.choice(_WORDS)}-{random.choice(_PREFIXES)}",
            lambda: f"{random.choice(_PREFIXES)}-{random.choice(_WORDS)}",
            lambda: f"{random.choice(_WORDS)}-{random.choice(_WORDS)}-{random.choice(_SUFFIXES)}",
            lambda: f"{random.choice(_PREFIXES)}-{random.choice(_WORDS)}-{random.choice(_SUFFIXES)}",
        ])()
        name = parts.lower().replace(" ", "-")
        # Vercel: max 52 chars, só letras/números/hífens
        name = name[:52]
        if name not in _USED_NAMES:
            _USED_NAMES.add(name)
            return name
    # fallback com sufixo numérico aleatório
    fallback = f"{random.choice(_WORDS)}-{random.randint(1000,9999)}"
    _USED_NAMES.add(fallback)
    return fallback


# ─────────────────────────────────────────────────────────────────────────────

def get_deployed_sites(urls_csv: Path) -> dict:
    """Retorna dict folder → row para sites já deployados."""
    done = {}
    if urls_csv.exists():
        with open(urls_csv, newline="") as f:
            for row in csv.DictReader(f):
                done[row["folder"]] = row
                _USED_NAMES.add(row["project"])   # evita reusar nomes
    return done


def deploy_site(site_dir: Path, project_name: str) -> str | None:
    cmd = [
        "vercel", "deploy",
        "--yes",
        "--prod",
        "--name", project_name,
        str(site_dir),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode == 0:
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        for line in reversed(lines):
            if line.startswith("https://"):
                return line
        return lines[-1] if lines else None

    return None


def run(start: int, end: int | None, resume: bool, limit: int | None, stop_on_error: bool = False) -> None:
    dataset_path = Path(DATASET_DIR)
    urls_csv     = Path(URLS_CSV)
    error_log    = Path(ERROR_LOG)

    if not dataset_path.exists():
        print(f"[!] Dataset não encontrado: {dataset_path.resolve()}")
        sys.exit(1)

    already_done = get_deployed_sites(urls_csv) if resume else {}
    if resume and already_done:
        print(f"[*] Resumindo — {len(already_done)} sites já deployados serão pulados.")

    site_dirs = sorted(dataset_path.glob("site_[0-9][0-9][0-9][0-9]"))
    if end:
        site_dirs = [d for d in site_dirs if start <= int(d.name.split("_")[1]) <= end]
    else:
        site_dirs = [d for d in site_dirs if int(d.name.split("_")[1]) >= start]

    total   = len(site_dirs)
    success = 0
    errors  = 0
    deployed_this_run = 0

    limit_str = f" (limite: {limit})" if limit else ""
    print(f"[*] {total} sites para fazer deploy → Vercel (nomes aleatórios){limit_str}")
    print(f"[*] URLs salvas em: {urls_csv.resolve()}\n")

    csv_exists = urls_csv.exists()
    csv_file   = open(urls_csv, "a", newline="")
    writer     = csv.DictWriter(csv_file, fieldnames=["folder", "project", "url", "status"])
    if not csv_exists:
        writer.writeheader()

    err_file = open(error_log, "a")

    for i, site_dir in enumerate(site_dirs, 1):
        folder_name = site_dir.name

        if limit and deployed_this_run >= limit:
            print(f"\n[*] Limite de {limit} deploys atingido. Rode novamente com --resume para continuar.")
            break

        if folder_name in already_done:
            row = already_done[folder_name]
            print(f"  [{i:>4}/{total}] {folder_name}  SKIP → {row['url']}")
            continue

        project_name = random_project_name()

        print(f"  [{i:>4}/{total}] {folder_name}  [{project_name}]  deploying... ", end="", flush=True)

        try:
            url = deploy_site(site_dir, project_name)
        except subprocess.TimeoutExpired:
            url = None
            err_file.write(f"TIMEOUT  {folder_name}  {project_name}\n")
        except Exception as e:
            url = None
            err_file.write(f"ERROR    {folder_name}  {project_name}  {e}\n")

        if url:
            print(f"OK → {url}")
            writer.writerow({"folder": folder_name, "project": project_name, "url": url, "status": "ok"})
            success += 1
            deployed_this_run += 1
        else:
            print("FALHOU")
            writer.writerow({"folder": folder_name, "project": project_name, "url": "", "status": "error"})
            err_file.write(f"FAILED   {folder_name}  {project_name}\n")
            errors += 1
            if stop_on_error:
                print(f"\n[!] Erro detectado — parando (--stop-on-error).")
                break

        csv_file.flush()
        err_file.flush()
        time.sleep(DELAY_SEC)

    csv_file.close()
    err_file.close()

    print(f"\n[+] Concluído: {success} OK  |  {errors} erros")
    print(f"[+] URLs: {urls_csv.resolve()}")
    if errors:
        print(f"[!] Erros: {error_log.resolve()}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GFE Dataset — Vercel Mass Deployer")
    parser.add_argument("--start",  type=int, default=1,    help="Site inicial (default: 1)")
    parser.add_argument("--end",    type=int, default=None, help="Site final (default: todos)")
    parser.add_argument("--resume", action="store_true",    help="Pula sites já presentes em deployed_urls.csv")
    parser.add_argument("--limit",          type=int, default=None, help="Para após N deploys bem-sucedidos (default: sem limite)")
    parser.add_argument("--stop-on-error",  action="store_true",    help="Para imediatamente no primeiro erro")
    args = parser.parse_args()

    run(start=args.start, end=args.end, resume=args.resume, limit=args.limit, stop_on_error=args.stop_on_error)
