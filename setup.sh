#!/usr/bin/env bash
# setup.sh - one-shot environment setup for bench-Compatible_windows.
#
# Clone the bench fork, run this file, then `bench init frappe-bench`.
#
#   git clone -b bench-6.1.0 https://github.com/azizios011/bench-Compatible_windows.git
#   cd bench-Compatible_windows && ./setup.sh
#
# Safe to re-run: every step checks what is already done.
#
# Optional environment variables:
#   NODE_VERSION=26.13.1   Node.js version installed through nvm
#   NVM_VERSION=0.41.0     nvm release to install
#   YARN_VERSION=1.22.22   Yarn Classic version (must be 1.x for --check-files)
#   SECURE_MARIADB=1       run mariadb-secure-installation (interactive) at the end

set -euo pipefail

NODE_VERSION="${NODE_VERSION:-26.13.1}"
NVM_VERSION="${NVM_VERSION:-0.41.0}"
YARN_VERSION="${YARN_VERSION:-1.22.22}"
SECURE_MARIADB="${SECURE_MARIADB:-0}"

BENCH_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- checks ---

[ -f "$BENCH_SRC/pyproject.toml" ] || die "Run this from inside the bench clone (pyproject.toml not found in $BENCH_SRC)."
command -v apt-get >/dev/null 2>&1 || die "This script targets Debian/Ubuntu (apt-get not found)."

if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
    warn "Running as root: bench, nvm and Node will be installed for root. Prefer a normal user."
else
    command -v sudo >/dev/null 2>&1 || die "sudo is required when not running as root."
    SUDO="sudo"
fi

# ---------------------------------------------- 1. OS packages + databases ---

log "1/5 Installing OS packages, Redis, MariaDB and C build headers"
$SUDO apt-get update
$SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git curl ca-certificates \
    python3-pip python3-venv python3-dev \
    pkg-config build-essential libffi-dev libssl-dev \
    redis-server mariadb-server mariadb-client \
    libmariadb-dev libmariadb-dev-compat
ok "Packages installed."

# ------------------------------------------------------ 2. Start services ---

log "2/5 Starting Redis and MariaDB"
start_service() {
    local svc="$1"
    if [ -d /run/systemd/system ]; then
        $SUDO systemctl enable --now "$svc" >/dev/null 2>&1 || $SUDO systemctl start "$svc" || true
    else
        $SUDO service "$svc" start || true
    fi
}
start_service redis-server
start_service mariadb

# Report status without failing the whole script.
if command -v redis-cli >/dev/null 2>&1 && redis-cli ping >/dev/null 2>&1; then
    ok "Redis is running."
else
    warn "Redis does not answer yet. Start it with: sudo service redis-server start"
fi
if command -v mariadb-admin >/dev/null 2>&1 && $SUDO mariadb-admin ping >/dev/null 2>&1; then
    ok "MariaDB is running."
else
    warn "MariaDB does not answer yet. Start it with: sudo service mariadb start"
fi

# ----------------------------------------- 3. PATH + bench (editable) -------

log "3/5 Exposing ~/.local/bin and installing bench (editable)"
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
touch "$HOME/.bashrc"
if ! grep -qxF "$PATH_LINE" "$HOME/.bashrc"; then
    printf '\n# added by bench setup.sh\n%s\n' "$PATH_LINE" >> "$HOME/.bashrc"
    ok "Added ~/.local/bin to ~/.bashrc."
else
    ok "~/.local/bin already in ~/.bashrc."
fi
export PATH="$HOME/.local/bin:$PATH"

# --break-system-packages bypasses Ubuntu's EXTERNALLY-MANAGED guard.
python3 -m pip install --user --break-system-packages -e "$BENCH_SRC"
ok "bench installed from $BENCH_SRC (also provides the run and repo commands)."

# ------------------------------------------------ 4. Node + Yarn Classic ----

log "4/5 Installing Node $NODE_VERSION (nvm $NVM_VERSION) and Yarn Classic $YARN_VERSION"
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/v${NVM_VERSION}/install.sh" | bash
fi
# nvm.sh is not nounset-safe.
set +u
# shellcheck disable=SC1091
. "$NVM_DIR/nvm.sh"
nvm install "$NODE_VERSION"
nvm alias default "$NODE_VERSION"
nvm use default >/dev/null
set -u

# Make sure future shells load nvm (the nvm installer normally does this already).
if ! grep -q 'NVM_DIR' "$HOME/.bashrc"; then
    {
        printf '\n# added by bench setup.sh\n'
        printf 'export NVM_DIR="$HOME/.nvm"\n'
        printf '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"\n'
    } >> "$HOME/.bashrc"
fi

npm install -g corepack
corepack enable
# Yarn Classic: bench runs `yarn install --check-files`, which Yarn Berry 4.x rejects.
corepack prepare "yarn@${YARN_VERSION}" --activate
ok "node $(node -v), yarn $(yarn --version)"

# ------------------------------------------------------------ 5. Verify -----

log "5/5 Verifying"
command -v bench >/dev/null 2>&1 && ok "bench: $(command -v bench)" || warn "bench not on PATH in this shell yet."
command -v run   >/dev/null 2>&1 && ok "run:   $(command -v run)"   || warn "run not on PATH in this shell yet."
command -v repo  >/dev/null 2>&1 && ok "repo:  $(command -v repo)"  || warn "repo not on PATH in this shell yet."
pkg-config --exists mariadb 2>/dev/null && ok "libmariadb headers found (mysqlclient will build)." \
    || warn "pkg-config cannot find libmariadb; mysqlclient may fail to build."

if [ "$SECURE_MARIADB" = "1" ]; then
    log "Running mariadb-secure-installation (interactive)"
    $SUDO mariadb-secure-installation
else
    warn "MariaDB root hardening skipped. Run 'sudo mariadb-secure-installation' once (or re-run with SECURE_MARIADB=1)."
fi

cat <<EOF

Done. Open a NEW terminal (or run: source ~/.bashrc), then:

    bench init frappe-bench

EOF
