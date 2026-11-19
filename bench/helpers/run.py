#!/usr/bin/env python3
"""
run — Axeane Kompta bench helper CLI.

Wraps common `bench` operations with shorter commands, defaulting to your
azizios011 forks and the axeane_kompta branch. Every flag can be overridden.

Usage:
  run init <bench_name> [--skip-assets] [extra flags...]
  run get-app <url_or_name> [<app2> ...] [--branch BRANCH] [--bench-dir DIR] [--overwrite] [--skip-assets]
  run site <site_name> [--bench-dir DIR] [--db-socket SOCK] [--db-root-user USER] [--db-root-password PWD] [--admin-password PWD] [--no-mariadb-socket]
  run install-app <site_name> <app> [<app2> ...] [--bench-dir DIR]
  run uninstall-app <site_name> <app> [<app2> ...] [--bench-dir DIR]
  run use <site_name> [--bench-dir DIR]
  run update [--bench-dir DIR] [--no-reset] [--patch]
  run start [--bench-dir DIR]
  run restart [--bench-dir DIR]
  run console [--bench-dir DIR]
  run build [--bench-dir DIR]
  run clean [--bench-dir DIR] [--hard]
  run nuke [bench_dir] [--yes]

Note: `run init` just wraps `bench init <name>` — your modified bench already
knows which repos/branches to pull, so this doesn't duplicate that config.

Examples:
  run init frappe-bench
  run get-app webshop --branch axeane_kompta
  run site kompta.local
  run install-app kompta.local tunisian_accounting
  run uninstall-app kompta.local tunisian_accounting
  run use kompta.local
  run update
  run start
  run restart
  run console
  run build
  run clean --hard
  run nuke --yes
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd, cwd=None):
    print(f"\n$ {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\n[!] Command failed (exit {result.returncode}): {' '.join(cmd)}")
        sys.exit(result.returncode)


def confirm(prompt):
    return input(f"{prompt} [y/N]: ").strip().lower() == "y"


def resolve_bench_dir(bench_dir_str="frappe-bench"):
    """Resolve bench directory.

    Returns the specified directory if it exists. If not, and the current
    working directory is itself a bench directory (contains 'sites/'),
    returns the current working directory.
    """
    bench_dir = Path(bench_dir_str)
    if bench_dir.exists():
        return bench_dir
    cwd = Path.cwd()
    if (cwd / "sites").is_dir():
        return cwd
    return bench_dir


# ---------------------------------------------------------------- init ----

def cmd_init(args, extra_args=None):
    bench_dir = Path(args.name)
    if bench_dir.exists():
        print(f"[!] '{bench_dir}' already exists. Aborting to avoid overwriting it.")
        sys.exit(1)

    cmd = ["bench", "init", args.name]
    if args.skip_assets:
        cmd.append("--skip-assets")
    if extra_args:
        cmd.extend(extra_args)
    run_cmd(cmd)
    print(f"[+] Bench '{args.name}' initialized.")


# ------------------------------------------------------------- get-app ----

def cmd_get_app(args, extra_args=None):
    bench_dir = resolve_bench_dir(args.bench_dir)
    if not bench_dir.exists():
        print(f"[!] Bench dir '{bench_dir}' not found. Pass --bench-dir if it's not 'frappe-bench'.")
        sys.exit(1)

    for app in args.apps:
        cmd = ["bench", "get-app", app]
        if args.branch:
            cmd += ["--branch", args.branch]
        if args.overwrite:
            cmd.append("--overwrite")
        if args.skip_assets:
            cmd.append("--skip-assets")
        if extra_args:
            cmd.extend(extra_args)
        run_cmd(cmd, cwd=bench_dir)
        print(f"[+] Successfully fetched app '{app}'.")


# ------------------------------------------------------------ list-apps ----

def cmd_list_apps(args):
    bench_dir = resolve_bench_dir(args.bench_dir)
    if not bench_dir.exists():
        print(f"[!] Bench dir '{bench_dir}' not found. Pass --bench-dir if it's not 'frappe-bench'.")
        sys.exit(1)
    cmd = ["bench"]
    if args.site:
        cmd += ["--site", args.site]
    cmd.append("list-apps")
    run_cmd(cmd, cwd=bench_dir)


# ---------------------------------------------------------------- site ----

def cmd_site(args, extra_args=None):
    bench_dir = resolve_bench_dir(args.bench_dir)
    if not bench_dir.exists():
        print(f"[!] Bench dir '{bench_dir}' not found. Run 'run init' first, or pass --bench-dir.")
        sys.exit(1)

    cmd = ["bench", "new-site", args.name]
    if args.db_root_user:
        cmd += ["--mariadb-root-username", args.db_root_user]
    if args.db_root_password:
        cmd += ["--mariadb-root-password", args.db_root_password]
    if args.admin_password:
        cmd += ["--admin-password", args.admin_password]
    if args.db_socket:
        cmd += ["--db-socket", args.db_socket]
    if args.no_mariadb_socket:
        cmd.append("--no-mariadb-socket")
    if extra_args:
        cmd.extend(extra_args)
    run_cmd(cmd, cwd=bench_dir)
    print(f"[+] Site '{args.name}' created. Use 'run install-app {args.name} <app>' next.")


# --------------------------------------------------------- install-app ----

def cmd_install_app(args):
    bench_dir = resolve_bench_dir(args.bench_dir)
    for app in args.apps:
        run_cmd(["bench", "--site", args.site, "install-app", app], cwd=bench_dir)
    print(f"[+] Installed {', '.join(args.apps)} on site '{args.site}'.")


# ------------------------------------------------------ uninstall-app ----

def cmd_uninstall_app(args):
    bench_dir = resolve_bench_dir(args.bench_dir)
    for app in args.apps:
        run_cmd(["bench", "--site", args.site, "uninstall-app", app], cwd=bench_dir)
    print(f"[+] Uninstalled {', '.join(args.apps)} from site '{args.site}'.")


# ----------------------------------------------------------------- use ----

def cmd_use(args):
    bench_dir = resolve_bench_dir(args.bench_dir)
    if not bench_dir.exists():
        print(f"[!] Bench dir '{bench_dir}' not found. Pass --bench-dir if it's not 'frappe-bench'.")
        sys.exit(1)
    run_cmd(["bench", "use", args.site], cwd=bench_dir)
    print(f"[+] Default site set to '{args.site}'. Future bench commands in this bench will target it.")


# -------------------------------------------------------------- update ----

def cmd_update(args):
    bench_dir = resolve_bench_dir(args.bench_dir)
    cmd = ["bench", "update"]
    if not args.no_reset:
        cmd.append("--reset")
    if args.patch:
        cmd.append("--patch")
    if args.no_backup:
        cmd.append("--no-backup")
    run_cmd(cmd, cwd=bench_dir)


# -------------------------------------------------------------- start ----

def cmd_start(args):
    bench_dir = resolve_bench_dir(args.bench_dir)
    run_cmd(["bench", "start"], cwd=bench_dir)


# ------------------------------------------------------------ restart ----

def cmd_restart(args):
    bench_dir = resolve_bench_dir(args.bench_dir)
    run_cmd(["bench", "restart"], cwd=bench_dir)


# ----------------------------------------------------------- console ----

def cmd_console(args):
    bench_dir = resolve_bench_dir(args.bench_dir)
    run_cmd(["bench", "console"], cwd=bench_dir)


# -------------------------------------------------------------- build ----

def cmd_build(args):
    bench_dir = resolve_bench_dir(args.bench_dir)
    run_cmd(["bench", "build", "--force"], cwd=bench_dir)


# --------------------------------------------------------------- clean ----

def cmd_clean(args):
    bench_dir = resolve_bench_dir(args.bench_dir)
    run_cmd(["bench", "clear-cache"], cwd=bench_dir)
    run_cmd(["bench", "clear-website-cache"], cwd=bench_dir)

    if args.hard:
        print("\n[*] Hard clean: removing __pycache__, .pyc, node cache, logs...")
        for p in bench_dir.rglob("__pycache__"):
            shutil.rmtree(p, ignore_errors=True)
        for p in bench_dir.rglob("*.pyc"):
            p.unlink(missing_ok=True)
        node_cache = bench_dir / "node_modules" / ".cache"
        if node_cache.exists():
            shutil.rmtree(node_cache, ignore_errors=True)
        logs_dir = bench_dir / "logs"
        if logs_dir.exists():
            for log in logs_dir.glob("*.log*"):
                log.unlink(missing_ok=True)
        print("[+] Hard clean complete.")


# ---------------------------------------------------------------- nuke ----

def list_sites(bench_dir):
    """Return site folder names under bench_dir/sites (skips non-site entries)."""
    sites_dir = bench_dir / "sites"
    if not sites_dir.is_dir():
        return []
    skip = {"assets", "common_site_config.json", "apps.txt", "apps.json", ".build"}
    return sorted(
        p.name for p in sites_dir.iterdir()
        if p.is_dir() and p.name not in skip and (p / "site_config.json").exists()
    )


def cmd_nuke(args):
    bench_dir = resolve_bench_dir(args.bench_dir)

    sites = list_sites(bench_dir)
    if sites:
        print(f"[*] Found {len(sites)} site(s) in '{bench_dir}': {', '.join(sites)}")
        if not args.yes and not confirm("Drop each site's database before deleting the bench dir?"):
            print("[!] Skipping DB drop — their databases will be left behind in MariaDB.")
            sites = []
    else:
        print(f"[*] No sites found under '{bench_dir}/sites' — nothing to drop in MariaDB.")

    for site in sites:
        cmd = ["bench", "drop-site", site, "--force"]
        if args.db_root_user:
            cmd += ["--root-login", args.db_root_user]
        if args.db_root_password:
            cmd += ["--root-password", args.db_root_password]
        run_cmd(cmd, cwd=bench_dir)

    if not args.yes and not confirm(f"DELETE the entire bench dir '{bench_dir}'? This cannot be undone."):
        print("Aborted.")
        return
    shutil.rmtree(bench_dir, ignore_errors=True)
    print(f"[+] Bench '{bench_dir}' deleted.")


# ---------------------------------------------------------------- main ----

def main():
    parser = argparse.ArgumentParser(prog="run", description="Axeane Kompta bench helper CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="bench init <name> [extra bench init flags...]")
    p_init.add_argument("name")
    p_init.add_argument("--skip-assets", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_get_app = sub.add_parser("get-app", help="bench get-app <name|url> [<app2> ...]")
    p_get_app.add_argument("apps", nargs="+", help="App name(s) or repository URL(s)")
    p_get_app.add_argument("--branch", default=None, help="Branch name to checkout")
    p_get_app.add_argument("--bench-dir", default="frappe-bench", help="Bench directory")
    p_get_app.add_argument("--overwrite", action="store_true", help="Overwrite existing app directory")
    p_get_app.add_argument("--skip-assets", action="store_true", help="Skip building assets")
    p_get_app.set_defaults(func=cmd_get_app)

    p_list_apps = sub.add_parser("list-apps", help="bench list-apps — show installed apps")
    p_list_apps.add_argument("site", nargs="?", default=None, help="Site name (optional, lists apps for a specific site)")
    p_list_apps.add_argument("--bench-dir", default="frappe-bench", help="Bench directory")
    p_list_apps.set_defaults(func=cmd_list_apps)

    p_site = sub.add_parser("site", help="bench new-site <name> (standalone, no app install)")
    p_site.add_argument("name")
    p_site.add_argument("--bench-dir", default="frappe-bench")
    p_site.add_argument("--db-root-user", default=None, dest="db_root_user")
    p_site.add_argument("--db-root-password", default=None, dest="db_root_password")
    p_site.add_argument("--admin-password", default=None)
    p_site.add_argument("--db-socket", default=None, help="Path to MariaDB UNIX socket")
    p_site.add_argument("--no-mariadb-socket", action="store_true")
    p_site.set_defaults(func=cmd_site)

    p_install = sub.add_parser("install-app", help="bench --site <site> install-app <app>")
    p_install.add_argument("site")
    p_install.add_argument("apps", nargs="+")
    p_install.add_argument("--bench-dir", default="frappe-bench")
    p_install.set_defaults(func=cmd_install_app)

    p_uninstall = sub.add_parser("uninstall-app", help="bench --site <site> uninstall-app <app>")
    p_uninstall.add_argument("site")
    p_uninstall.add_argument("apps", nargs="+")
    p_uninstall.add_argument("--bench-dir", default="frappe-bench")
    p_uninstall.set_defaults(func=cmd_uninstall_app)

    p_use = sub.add_parser("use", help="bench use <site> — set the default site for this bench")
    p_use.add_argument("site")
    p_use.add_argument("--bench-dir", default="frappe-bench")
    p_use.set_defaults(func=cmd_use)

    p_update = sub.add_parser("update", help="bench update --reset")
    p_update.add_argument("--bench-dir", default="frappe-bench")
    p_update.add_argument("--no-reset", action="store_true")
    p_update.add_argument("--patch", action="store_true")
    p_update.add_argument("--no-backup", action="store_true")
    p_update.set_defaults(func=cmd_update)

    p_start = sub.add_parser("start", help="bench start")
    p_start.add_argument("--bench-dir", default="frappe-bench")
    p_start.set_defaults(func=cmd_start)

    p_restart = sub.add_parser("restart", help="bench restart")
    p_restart.add_argument("--bench-dir", default="frappe-bench")
    p_restart.set_defaults(func=cmd_restart)

    p_console = sub.add_parser("console", help="bench console")
    p_console.add_argument("--bench-dir", default="frappe-bench")
    p_console.set_defaults(func=cmd_console)

    p_build = sub.add_parser("build", help="bench build --force")
    p_build.add_argument("--bench-dir", default="frappe-bench")
    p_build.set_defaults(func=cmd_build)

    p_clean = sub.add_parser("clean", help="bench clear-cache [--hard]")
    p_clean.add_argument("--bench-dir", default="frappe-bench")
    p_clean.add_argument("--hard", action="store_true", help="also wipe __pycache__, node cache, logs")
    p_clean.set_defaults(func=cmd_clean)

    p_nuke = sub.add_parser("nuke", help="drop every site's DB then delete the whole bench dir")
    p_nuke.add_argument("bench_dir", nargs="?", default="frappe-bench",
                        help="bench directory to delete (default: frappe-bench)")
    p_nuke.add_argument("--db-root-user", default=None, dest="db_root_user")
    p_nuke.add_argument("--db-root-password", default=None, dest="db_root_password")
    p_nuke.add_argument("--yes", action="store_true", help="skip confirmation prompts")
    p_nuke.set_defaults(func=cmd_nuke)

    args, extra_args = parser.parse_known_args()
    import inspect
    sig = inspect.signature(args.func)
    if "extra_args" in sig.parameters:
        args.func(args, extra_args=extra_args)
    else:
        if extra_args:
            parser.error(f"unrecognized arguments: {' '.join(extra_args)}")
        args.func(args)


if __name__ == "__main__":
    main()
