"""
GFE — Redeploy com novo webhook
Atualiza o action= nos HTMLs existentes e redeploye nos mesmos projetos Vercel.

Uso:
    python3 redeploy_webhook.py
    python3 redeploy_webhook.py --dry-run        # só mostra o que faria
    python3 redeploy_webhook.py --start 501 --end 510
"""

import csv
import subprocess
import time
import argparse
import sys
from pathlib import Path

DATASET_DIR  = Path("./gfe_dataset")
URLS_CSV     = Path("./deployed_urls.csv")
ERROR_LOG    = Path("./deploy_errors.log")
NEW_WEBHOOK  = "https://webhook.site/c64f18e9-e599-48b4-b3ba-366dc9700b22"
OLD_WEBHOOK  = "https://webhook.site/SEU-ID-AQUI"
DELAY_SEC    = 1.5


def load_deployed() -> dict:
    """folder → project_name para sites com status ok."""
    deployed = {}
    if not URLS_CSV.exists():
        print(f"[!] {URLS_CSV} não encontrado.")
        sys.exit(1)
    with open(URLS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("status", "").strip().lower() == "ok":
                deployed[row["folder"]] = row["project"]
    return deployed


def patch_html(site_dir: Path) -> bool:
    """Substitui o webhook no index.html. Retorna True se alterou."""
    html_path = site_dir / "index.html"
    if not html_path.exists():
        return False
    content = html_path.read_text(encoding="utf-8")
    if OLD_WEBHOOK not in content and NEW_WEBHOOK in content:
        return False  # já atualizado
    new_content = content.replace(OLD_WEBHOOK, NEW_WEBHOOK)
    if new_content == content:
        return False
    html_path.write_text(new_content, encoding="utf-8")
    return True


def deploy_site(site_dir: Path, project_name: str) -> str | None:
    cmd = ["vercel", "deploy", "--yes", "--prod", "--name", project_name, str(site_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        for line in reversed(lines):
            if line.startswith("https://"):
                return line
        return lines[-1] if lines else None
    return None


def run(start: int, end: int | None, dry_run: bool, force: bool) -> None:
    deployed = load_deployed()

    folders = sorted(deployed.keys())
    if end:
        folders = [f for f in folders if start <= int(f.split("_")[1]) <= end]
    else:
        folders = [f for f in folders if int(f.split("_")[1]) >= start]

    total   = len(folders)
    patched = 0
    success = 0
    errors  = 0

    print(f"[*] {total} sites para atualizar | webhook: {NEW_WEBHOOK}")
    if dry_run:
        print("[*] DRY-RUN — nenhuma alteração será feita\n")
    if force:
        print("[*] FORCE — redeployando mesmo sem mudança no HTML\n")

    err_file = open(ERROR_LOG, "a") if not dry_run else None

    for i, folder in enumerate(folders, 1):
        project   = deployed[folder]
        site_dir  = DATASET_DIR / folder

        changed = patch_html(site_dir)
        should_deploy = changed or force
        status  = "PATCH" if changed else ("FORCE" if force else "SKIP (já atualizado)")

        print(f"  [{i:>4}/{total}] {folder}  [{project}]  {status}", end="", flush=True)

        if dry_run or not should_deploy:
            print()
            continue

        patched += 1
        print("  deploying...", end="", flush=True)

        try:
            url = deploy_site(site_dir, project)
        except subprocess.TimeoutExpired:
            url = None
            err_file.write(f"TIMEOUT  {folder}  {project}\n")
        except Exception as e:
            url = None
            err_file.write(f"ERROR    {folder}  {project}  {e}\n")

        if url:
            print(f"  OK → {url}")
            success += 1
        else:
            print("  FALHOU")
            errors += 1
            err_file.write(f"FAILED   {folder}  {project}\n")

        if err_file:
            err_file.flush()
        time.sleep(DELAY_SEC)

    if err_file:
        err_file.close()

    print(f"\n[+] HTMLs atualizados: {patched}/{total} | Deploys OK: {success} | Erros: {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GFE — Redeploy com novo webhook")
    parser.add_argument("--start",   type=int, default=1,    help="Site inicial (default: 1)")
    parser.add_argument("--end",     type=int, default=None, help="Site final (default: todos)")
    parser.add_argument("--dry-run", action="store_true",    help="Só mostra o que faria, sem alterar nada")
    parser.add_argument("--force",   action="store_true",    help="Redeploye mesmo sem mudança no HTML")
    args = parser.parse_args()

    run(start=args.start, end=args.end, dry_run=args.dry_run, force=args.force)
