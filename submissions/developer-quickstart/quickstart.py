#!/usr/bin/env python3
"""RustChain Developer Quickstart — one-command dev environment setup (Python)."""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────

DEFAULT_CHAIN_ID = os.getenv("RUSTCHAIN_CHAIN_ID", "local-testnet")
DEFAULT_MONIKER = os.getenv("RUSTCHAIN_MONIKER", "dev-node")
DEFAULT_DENOM = os.getenv("RUSTCHAIN_DENOM", "urst")
DEFAULT_HOME = os.getenv("RUSTCHAIN_HOME", str(Path.home() / ".rustchain"))
KEYRING_BACKEND = "test"
FAUCET_MNEMONIC = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
FAUCET_KEY = "faucet"
DEV_KEY = "dev"

# ── Helpers ─────────────────────────────────────────────────────────────────

def info(msg: str):
    print(f"  \033[94m[INFO]\033[0m {msg}")

def ok(msg: str):
    print(f"  \033[92m[OK]\033[0m {msg}")

def warn(msg: str):
    print(f"  \033[93m[WARN]\033[0m {msg}")

def fail(msg: str):
    print(f"  \033[91m[FAIL]\033[0m {msg}")
    sys.exit(1)

def run(cmd: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    result = subprocess.run(
        cmd, shell=True, capture_output=capture, text=True,
        timeout=300,
    )
    if check and result.returncode != 0:
        if capture:
            warn(f"Command failed: {cmd}\n  stderr: {result.stderr.strip()}")
        return result
    return result

def cmd_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


# ── Steps ───────────────────────────────────────────────────────────────────

def check_dependencies():
    """Step 1: Check system dependencies."""
    info("Checking system dependencies...")
    required = ["git"]
    optional = ["go", "gcc", "make"]

    missing = []
    for cmd in required:
        if cmd_exists(cmd):
            ok(f"{cmd} found")
        else:
            missing.append(cmd)
            warn(f"{cmd} not found (required)")

    for cmd in optional:
        if cmd_exists(cmd):
            ok(f"{cmd} found")
        else:
            warn(f"{cmd} not found (optional)")

    if missing:
        fail(f"Missing required dependencies: {', '.join(missing)}")


def install_binary(args):
    """Step 2: Install rustchaind."""
    if cmd_exists("rustchaind") and not args.reset:
        ok("rustchaind already installed")
        return

    info("Installing rustchaind...")

    if args.download:
        arch = platform.machine().lower()
        os_name = platform.system().lower()
        url = f"https://github.com/rustchain/rustchain/releases/latest/download/rustchaind-{os_name}-{arch}"
        info(f"Downloading from {url}")
        result = run(f"curl -sL {url} -o /usr/local/bin/rustchaind", check=False, capture=True)
        if result.returncode == 0:
            run("chmod +x /usr/local/bin/rustchaind", check=False)
            if cmd_exists("rustchaind"):
                ok("rustchaind downloaded")
                return
        warn("Download failed, trying source build...")

    # Try building from source
    src_dir = Path.home() / "rustchain-src"
    if not src_dir.exists():
        info("Cloning RustChain source...")
        run(f"git clone https://github.com/rustchain/rustchain.git {src_dir}", check=False, capture=True)

    info("Building rustchaind...")
    result = run(f"cd {src_dir} && make install", check=False, capture=True)
    if result.returncode != 0:
        result = run(f"cd {src_dir} && go build -o /usr/local/bin/rustchaind ./cmd/rustchaind", check=False, capture=True)

    if cmd_exists("rustchaind"):
        ok("rustchaind installed")
    else:
        fail("Failed to install rustchaind")


def initialize_node(args):
    """Step 3: Initialize node."""
    home = args.home

    if args.reset and Path(home).exists():
        warn(f"Resetting {home}...")
        shutil.rmtree(home, ignore_errors=True)
        ok("Reset complete")

    info(f"Initializing node (chain: {args.chain_id}, moniker: {args.moniker})...")
    run(f'rustchaind init "{args.moniker}" --chain-id {args.chain_id} --home {home}', check=False, capture=True)
    ok("Node initialized")


def configure_node(args):
    """Step 4: Configure node."""
    home = args.home
    info("Configuring node...")
    for cfg in [
        f"chain-id {args.chain_id}",
        f"keyring-backend {KEYRING_BACKEND}",
        "output json",
    ]:
        run(f"rustchaind config {cfg} --home {home}", check=False, capture=True)
    ok("Configuration set")


def create_keys(args):
    """Step 5: Create development keys."""
    home = args.home
    info("Setting up development keys...")

    # Faucet key
    run(f'echo "{FAUCET_MNEMONIC}" | rustchaind keys add {FAUCET_KEY} --recover --keyring-backend {KEYRING_BACKEND} --home {home}', check=False, capture=True)

    # Dev key
    run(f"rustchaind keys add {DEV_KEY} --keyring-backend {KEYRING_BACKEND} --home {home}", check=False, capture=True)

    faucet_addr = run(f"rustchaind keys show {FAUCET_KEY} -a --keyring-backend {KEYRING_BACKEND} --home {home}", check=False, capture=True)
    dev_addr = run(f"rustchaind keys show {DEV_KEY} -a --keyring-backend {KEYRING_BACKEND} --home {home}", check=False, capture=True)

    faucet = faucet_addr.stdout.strip() if faucet_addr.returncode == 0 else "unknown"
    dev = dev_addr.stdout.strip() if dev_addr.returncode == 0 else "unknown"

    ok("Keys created:")
    print(f"    Faucet: {faucet}")
    print(f"    Dev:    {dev}")
    return faucet, dev


def setup_genesis(args, faucet: str, dev: str):
    """Step 6: Genesis setup."""
    if args.mode == "minimal":
        return

    home = args.home
    denom = args.denom
    info("Setting up genesis...")

    run(f'rustchaind add-genesis-account {FAUCET_KEY} "100000000000{denom}" --keyring-backend {KEYRING_BACKEND} --home {home}', check=False, capture=True)
    run(f'rustchaind add-genesis-account {DEV_KEY} "10000000000{denom}" --keyring-backend {KEYRING_BACKEND} --home {home}', check=False, capture=True)
    run(f'rustchaind gentx {FAUCET_KEY} "1000000000{denom}" --chain-id {args.chain_id} --keyring-backend {KEYRING_BACKEND} --home {home}', check=False, capture=True)
    run(f"rustchaind collect-gentxs --home {home}", check=False, capture=True)

    ok("Genesis configured")


def create_scripts(args, faucet: str):
    """Step 7: Create helper scripts."""
    home = args.home
    scripts_dir = Path(home) / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    # start.sh
    start_script = scripts_dir / "start.sh"
    start_script.write_text(f"""#!/bin/bash
# Start local RustChain node
RUSTCHAIN_HOME="${{RUSTCHAIN_HOME:-{home}}}"
rustchaind start --home "$RUSTCHAIN_HOME" "$@"
""")
    start_script.chmod(0o755)

    # faucet.sh
    faucet_script = scripts_dir / "faucet.sh"
    faucet_script.write_text(f"""#!/bin/bash
# Send tokens from faucet
RUSTCHAIN_HOME="${{RUSTCHAIN_HOME:-{home}}}"
TO=${{1:?"Usage: faucet.sh <address> [amount]"}}
AMOUNT=${{2:-"1000000{args.denom}"}}
rustchaind tx bank send {FAUCET_KEY} "$TO" "$AMOUNT" --keyring-backend test --home "$RUSTCHAIN_HOME" --yes --chain-id {args.chain_id}
""")
    faucet_script.chmod(0o755)

    # Python helper
    helper_py = scripts_dir / "helper.py"
    helper_py.write_text('''#!/usr/bin/env python3
"""RustChain dev helper — common operations."""
import subprocess, sys

def run(cmd):
    return subprocess.run(cmd, shell=True).returncode

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: helper.py [status|balance|validators|keys]")
        sys.exit(1)
    cmds = {
        "status": "rustchaind status",
        "balance": f"rustchaind query bank balances {sys.argv[2] if len(sys.argv) > 2 else ''}",
        "validators": "rustchaind query staking validators",
        "keys": "rustchaind keys list --keyring-backend test",
    }
    cmd = cmds.get(sys.argv[1])
    if cmd:
        run(cmd)
    else:
        print(f"Unknown: {sys.argv[1]}")
''')

    ok(f"Scripts created in {scripts_dir}/")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RustChain Developer Quickstart")
    parser.add_argument("--mode", choices=["full", "minimal"], default="full",
                        help="Setup mode (default: full)")
    parser.add_argument("--download", action="store_true",
                        help="Download binary instead of building")
    parser.add_argument("--chain-id", default=DEFAULT_CHAIN_ID,
                        help=f"Chain ID (default: {DEFAULT_CHAIN_ID})")
    parser.add_argument("--moniker", default=DEFAULT_MONIKER,
                        help=f"Node moniker (default: {DEFAULT_MONIKER})")
    parser.add_argument("--denom", default=DEFAULT_DENOM,
                        help=f"Token denomination (default: {DEFAULT_DENOM})")
    parser.add_argument("--home", default=DEFAULT_HOME,
                        help=f"Node home directory (default: {DEFAULT_HOME})")
    parser.add_argument("--reset", action="store_true",
                        help="Reset existing data directory")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  RustChain Developer Quickstart")
    print(f"{'='*60}\n")

    check_dependencies()
    install_binary(args)
    initialize_node(args)
    configure_node(args)
    faucet, dev = create_keys(args)
    setup_genesis(args, faucet, dev)
    create_scripts(args, faucet)

    print(f"\n{'='*60}")
    print(f"  \033[92m✓ RustChain Development Environment Ready!\033[0m")
    print(f"{'='*60}")
    print(f"""
  Chain ID:    {args.chain_id}
  Home:        {args.home}
  Faucet:      {faucet}
  Dev:         {dev}

  Start node:  {args.home}/scripts/start.sh
  Use faucet:  {args.home}/scripts/faucet.sh <address>

  Happy building! 🦀
""")


if __name__ == "__main__":
    main()
