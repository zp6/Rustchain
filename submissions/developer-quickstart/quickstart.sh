#!/usr/bin/env bash
# RustChain Developer Quickstart — one-command dev environment setup
set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
CHAIN_ID="${RUSTCHAIN_CHAIN_ID:-local-testnet}"
MONIKER="${RUSTCHAIN_MONIKER:-dev-node}"
DENOM="${RUSTCHAIN_DENOM:-urst}"
HOME_DIR="${RUSTCHAIN_HOME:-$HOME/.rustchain}"
KEYRING_BACKEND="test"
FAUCET_MNEMONIC="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
FAUCET_KEY="faucet"
DEV_KEY="dev"

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# ── Parse args ──────────────────────────────────────────────────────────────
MODE="full"
DOWNLOAD=false
RESET=false
WITH_MONITORING=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full)          MODE="full"; shift ;;
        --minimal)       MODE="minimal"; shift ;;
        --download)      DOWNLOAD=true; shift ;;
        --chain-id)      CHAIN_ID="$2"; shift 2 ;;
        --moniker)       MONIKER="$2"; shift 2 ;;
        --reset)         RESET=true; shift ;;
        --with-monitoring) WITH_MONITORING=true; shift ;;
        --help|-h)       echo "Usage: $0 [--full|--minimal] [--download] [--chain-id ID] [--moniker NAME] [--reset] [--with-monitoring]"; exit 0 ;;
        *)               warn "Unknown option: $1"; shift ;;
    esac
done

# ── Step 1: Check dependencies ─────────────────────────────────────────────
info "Checking system dependencies..."

check_cmd() {
    if command -v "$1" &>/dev/null; then
        ok "$1 found ($(command -v "$1"))"
        return 0
    else
        return 1
    fi
}

MISSING=()
for cmd in go git make gcc; do
    check_cmd "$cmd" || MISSING+=("$cmd")
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    warn "Missing: ${MISSING[*]}"
    if [[ "$MODE" == "full" ]]; then
        info "Attempting to install missing dependencies..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y -qq "${MISSING[@]}" 2>/dev/null || true
        elif command -v brew &>/dev/null; then
            for m in "${MISSING[@]}"; do brew install "$m" 2>/dev/null || true; done
        fi
    fi
fi

# ── Step 2: Install rustchaind ─────────────────────────────────────────────
if command -v rustchaind &>/dev/null && [[ "$RESET" != true ]]; then
    ok "rustchaind already installed"
else
    info "Installing rustchaind..."
    
    if [[ "$DOWNLOAD" == true ]]; then
        # Download pre-built binary
        ARCH=$(uname -m)
        OS=$(uname -s | tr '[:upper:]' '[:lower:]')
        BINARY_URL="https://github.com/rustchain/rustchain/releases/latest/download/rustchaind-${OS}-${ARCH}"
        info "Downloading from $BINARY_URL"
        curl -sL "$BINARY_URL" -o /usr/local/bin/rustchaind || {
            warn "Download failed, trying to build from source..."
            DOWNLOAD=false
        }
        chmod +x /usr/local/bin/rustchaind 2>/dev/null || true
    fi

    if [[ "$DOWNLOAD" == false ]]; then
        # Build from source
        if [[ ! -d "${HOME}/rustchain-src" ]]; then
            info "Cloning RustChain source..."
            git clone https://github.com/rustchain/rustchain.git "${HOME}/rustchain-src" 2>/dev/null || true
        fi
        info "Building rustchaind..."
        cd "${HOME}/rustchain-src"
        make install 2>/dev/null || go build -o /usr/local/bin/rustchaind ./cmd/rustchaind 2>/dev/null || {
            warn "Build failed. Trying go install..."
            go install github.com/rustchain/rustchain/cmd/rustchaind@latest 2>/dev/null || true
        }
    fi
    
    command -v rustchaind &>/dev/null && ok "rustchaind installed" || fail "Failed to install rustchaind"
fi

# ── Step 3: Reset if needed ────────────────────────────────────────────────
if [[ "$RESET" == true ]] && [[ -d "$HOME_DIR" ]]; then
    warn "Resetting $HOME_DIR..."
    rm -rf "$HOME_DIR"
    ok "Reset complete"
fi

# ── Step 4: Initialize node ────────────────────────────────────────────────
info "Initializing node (chain: $CHAIN_ID, moniker: $MONIKER)..."
rustchaind init "$MONIKER" --chain-id "$CHAIN_ID" --home "$HOME_DIR" 2>/dev/null || true
ok "Node initialized"

# ── Step 5: Configure ──────────────────────────────────────────────────────
info "Configuring node..."
rustchaind config chain-id "$CHAIN_ID" --home "$HOME_DIR" 2>/dev/null || true
rustchaind config keyring-backend "$KEYRING_BACKEND" --home "$HOME_DIR" 2>/dev/null || true
rustchaind config output json --home "$HOME_DIR" 2>/dev/null || true
ok "Configuration set"

# ── Step 6: Create keys ────────────────────────────────────────────────────
info "Setting up development keys..."

# Faucet key
echo "$FAUCET_MNEMONIC" | rustchaind keys add "$FAUCET_KEY" --recover --keyring-backend "$KEYRING_BACKEND" --home "$HOME_DIR" 2>/dev/null || true

# Dev key (random)
rustchaind keys add "$DEV_KEY" --keyring-backend "$KEYRING_BACKEND" --home "$HOME_DIR" 2>/dev/null || true

FAUCET_ADDR=$(rustchaind keys show "$FAUCET_KEY" -a --keyring-backend "$KEYRING_BACKEND" --home "$HOME_DIR" 2>/dev/null || echo "unknown")
DEV_ADDR=$(rustchaind keys show "$DEV_KEY" -a --keyring-backend "$KEYRING_BACKEND" --home "$HOME_DIR" 2>/dev/null || echo "unknown")

ok "Keys created:"
echo "  Faucet: $FAUCET_ADDR"
echo "  Dev:    $DEV_ADDR"

# ── Step 7: Genesis setup ──────────────────────────────────────────────────
if [[ "$MODE" == "full" ]]; then
    info "Setting up genesis..."
    
    # Add faucet to genesis with funds
    rustchaind add-genesis-account "$FAUCET_KEY" "100000000000${DENOM}" --keyring-backend "$KEYRING_BACKEND" --home "$HOME_DIR" 2>/dev/null || true
    rustchaind add-genesis-account "$DEV_KEY" "10000000000${DENOM}" --keyring-backend "$KEYRING_BACKEND" --home "$HOME_DIR" 2>/dev/null || true
    
    # Create validator
    rustchaind gentx "$FAUCET_KEY" "1000000000${DENOM}" --chain-id "$CHAIN_ID" --keyring-backend "$KEYRING_BACKEND" --home "$HOME_DIR" 2>/dev/null || true
    rustchaind collect-gentxs --home "$HOME_DIR" 2>/dev/null || true
    
    ok "Genesis configured"
fi

# ── Step 8: Helper scripts ─────────────────────────────────────────────────
info "Creating helper scripts..."
mkdir -p "$HOME_DIR/scripts"

cat > "$HOME_DIR/scripts/start.sh" << 'SCRIPT'
#!/bin/bash
# Start local RustChain node
RUSTCHAIN_HOME="${RUSTCHAIN_HOME:-$HOME/.rustchain}"
rustchaind start --home "$RUSTCHAIN_HOME" "$@"
SCRIPT
chmod +x "$HOME_DIR/scripts/start.sh"

cat > "$HOME_DIR/scripts/faucet.sh" << SCRIPT
#!/bin/bash
# Send tokens from faucet
RUSTCHAIN_HOME="${RUSTCHAIN_HOME:-$HOME/.rustchain}"
TO=\${1:?"Usage: faucet.sh <address> [amount]"}
AMOUNT=\${2:-"1000000${DENOM}"}
rustchaind tx bank send $FAUCET_KEY "\$TO" "\$AMOUNT" --keyring-backend test --home "\$RUSTCHAIN_HOME" --yes --chain-id "$CHAIN_ID"
SCRIPT
chmod +x "$HOME_DIR/scripts/faucet.sh"

ok "Scripts created in $HOME_DIR/scripts/"

# ── Step 9: Monitoring (optional) ──────────────────────────────────────────
if [[ "$WITH_MONITORING" == true ]]; then
    info "Setting up monitoring..."
    # Would install prometheus/grafana exporters here
    warn "Monitoring setup is a placeholder — configure manually for now"
fi

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════"
echo -e "${GREEN}  ✓ RustChain Development Environment Ready!${NC}"
echo "══════════════════════════════════════════════════════════"
echo ""
echo "  Chain ID:    $CHAIN_ID"
echo "  Home:        $HOME_DIR"
echo "  Faucet:      $FAUCET_ADDR"
echo "  Dev:         $DEV_ADDR"
echo ""
echo "  Start node:  $HOME_DIR/scripts/start.sh"
echo "  Use faucet:  $HOME_DIR/scripts/faucet.sh <address>"
echo ""
echo "  Happy building! 🦀"
echo ""
