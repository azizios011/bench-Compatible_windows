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
# Pinned versions (override with environment variables):
#   MARIADB_VERSION=11.8.6   MariaDB server/client
#   REDIS_VERSION=8.0.5      Redis server/tools
#   NODE_VERSION=26.13.1     Node.js (through nvm)
#   NPM_VERSION=12.2.3       npm
#   YARN_VERSION=1.22.22     Yarn Classic (must be 1.x for --check-files)
#   PNPM_VERSION=12.21.0     pnpm (through corepack)
#   NVM_VERSION=0.41.0       nvm release to install
#   SECURE_MARIADB=1         run mariadb-secure-installation (interactive) at the end

set -euo pipefail

MARIADB_VERSION="${MARIADB_VERSION:-11.8.6}"
REDIS_VERSION="${REDIS_VERSION:-8.0.5}"
NODE_VERSION="${NODE_VERSION:-26.13.1}"
NPM_VERSION="${NPM_VERSION:-12.2.3}"
YARN_VERSION="${YARN_VERSION:-1.22.22}"
PNPM_VERSION="${PNPM_VERSION:-12.21.0}"
NVM_VERSION="${NVM_VERSION:-0.41.0}"
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

# shellcheck disable=SC1091
. /etc/os-release
CODENAME="${VERSION_CODENAME:-}"
DISTRO_ID="${ID:-ubuntu}"

pkg_installed() { dpkg-query -W -f='${Version}' "$1" 2>/dev/null || true; }
pkg_candidate() { apt-cache policy "$1" 2>/dev/null | awk '/Candidate:/{print $2}'; }

# ----------------------------------------------- 1. Base OS packages -------

log "1/6 Installing base OS packages and C build headers"
$SUDO apt-get update
$SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git curl ca-certificates gnupg \
    python3-pip python3-venv python3-dev \
    pkg-config build-essential libffi-dev libssl-dev
ok "Base packages installed."

# ------------------------------------------ 2. MariaDB (pinned) ------------

log "2/6 MariaDB $MARIADB_VERSION"
add_mariadb_repo() {
    case "$DISTRO_ID" in ubuntu|debian) ;; *) die "No MariaDB repo mapping for distro '$DISTRO_ID'." ;; esac
    [ -n "$CODENAME" ] || die "Cannot detect the distro codename for the MariaDB repo."
    warn "Distro packages are not MariaDB $MARIADB_VERSION; adding the official MariaDB repo ($CODENAME)."
    $SUDO mkdir -p /etc/apt/keyrings
    $SUDO curl -fsSL https://mariadb.org/mariadb_release_signing_key.pgp -o /etc/apt/keyrings/mariadb-keyring.pgp
    echo "deb [signed-by=/etc/apt/keyrings/mariadb-keyring.pgp] https://archive.mariadb.org/mariadb-${MARIADB_VERSION}/repo/${DISTRO_ID} ${CODENAME} main" \
        | $SUDO tee /etc/apt/sources.list.d/mariadb.list >/dev/null
    $SUDO apt-get update
}

installed_maria="$(pkg_installed mariadb-server)"
if [ -n "$installed_maria" ]; then
    case "$installed_maria" in
        *"$MARIADB_VERSION"*) ok "MariaDB $installed_maria already installed." ;;
        *) warn "MariaDB $installed_maria is installed (wanted $MARIADB_VERSION). Not touching an existing database server; remove it first if you want the pinned version." ;;
    esac
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y libmariadb-dev libmariadb-dev-compat
else
    case "$(pkg_candidate mariadb-server)" in
        *"$MARIADB_VERSION"*) ;;
        *) add_mariadb_repo ;;
    esac
    printf 'Package: mariadb-*\nPin: version *%s*\nPin-Priority: 1001\n' "$MARIADB_VERSION" \
        | $SUDO tee /etc/apt/preferences.d/mariadb-pin >/dev/null
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y \
        mariadb-server mariadb-client libmariadb-dev libmariadb-dev-compat
fi

# -------------------------------------------- 3. Redis (pinned) ------------

log "3/6 Redis $REDIS_VERSION"
add_redis_repo() {
    [ -n "$CODENAME" ] || die "Cannot detect the distro codename for the Redis repo."
    warn "Distro packages are not Redis $REDIS_VERSION; adding the official Redis repo ($CODENAME)."
    curl -fsSL https://packages.redis.io/gpg | $SUDO gpg --batch --yes --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
    $SUDO chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb ${CODENAME} main" \
        | $SUDO tee /etc/apt/sources.list.d/redis.list >/dev/null
    $SUDO apt-get update
}

installed_redis="$(pkg_installed redis-server)"
if [ -n "$installed_redis" ]; then
    case "$installed_redis" in
        *"$REDIS_VERSION"*) ok "Redis $installed_redis already installed." ;;
        *) warn "Redis $installed_redis is installed (wanted $REDIS_VERSION). Not changing it; remove it first if you want the pinned version." ;;
    esac
else
    case "$(pkg_candidate redis-server)" in
        *"$REDIS_VERSION"*) ;;
        *) add_redis_repo ;;
    esac
    printf 'Package: redis*\nPin: version *%s*\nPin-Priority: 1001\n' "$REDIS_VERSION" \
        | $SUDO tee /etc/apt/preferences.d/redis-pin >/dev/null
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y redis-server redis-tools
fi

# ------------------------------------------------------ 4. Start services ---

log "4/6 Starting Redis and MariaDB"
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

# ----------------------------------------- 5. PATH + bench (editable) -------

log "5/6 Exposing ~/.local/bin and installing bench (editable)"
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

# --------------------------------- 6. Node, npm, Yarn Classic, pnpm ---------

log "6/6 Node $NODE_VERSION, npm $NPM_VERSION, Yarn $YARN_VERSION, pnpm $PNPM_VERSION"
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

if ! grep -q 'NVM_DIR' "$HOME/.bashrc"; then
    {
        printf '\n# added by bench setup.sh\n'
        printf 'export NVM_DIR="$HOME/.nvm"\n'
        printf '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"\n'
    } >> "$HOME/.bashrc"
fi

npm install -g "npm@${NPM_VERSION}"
npm install -g corepack
corepack enable
# Yarn Classic: bench runs `yarn install --check-files`, which Yarn Berry 4.x rejects.
corepack prepare "yarn@${YARN_VERSION}" --activate
corepack prepare "pnpm@${PNPM_VERSION}" --activate

# ------------------------------------------------------------ Verify --------

log "Verifying"
check_ver() { # name, wanted, actual
    case "$3" in
        *"$2"*) ok "$1 $3" ;;
        *) warn "$1: wanted $2, got '$3'" ;;
    esac
}
check_ver "mariadb" "$MARIADB_VERSION" "$(mariadb --version 2>/dev/null || echo missing)"
check_ver "redis"   "$REDIS_VERSION"   "$(redis-server --version 2>/dev/null || echo missing)"
check_ver "node"    "$NODE_VERSION"    "$(node -v)"
check_ver "npm"     "$NPM_VERSION"     "$(npm -v)"
check_ver "yarn"    "$YARN_VERSION"    "$(yarn --version)"
check_ver "pnpm"    "$PNPM_VERSION"    "$(pnpm --version)"

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

cat <<MSG

Done. Open a NEW terminal (or run: source ~/.bashrc), then:

    bench init frappe-bench

MSG
