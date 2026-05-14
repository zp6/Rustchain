#!/usr/bin/env python3
"""RustChain Delegation Tracker — track delegations, rewards, and export CSV."""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────

DEFAULT_RPC = os.getenv("RUSTCHAIN_RPC", "https://rpc.rustchain.io")
DEFAULT_API = os.getenv("RUSTCHAIN_API", "https://api.rustchain.io")
CHAIN_ID = os.getenv("RUSTCHAIN_CHAIN_ID", "rustchain-1")
DENOM = os.getenv("RUSTCHAIN_DENOM", "urst")
DENOM_DISPLAY = os.getenv("RUSTCHAIN_DENOM_DISPLAY", "RUST")
DECIMALS = int(os.getenv("RUSTCHAIN_DECIMALS", "6"))

# ── Helpers ─────────────────────────────────────────────────────────────────

def to_display(amount_str: str) -> str:
    """Convert on-chain amount (uint) to display denom."""
    try:
        val = int(amount_str) / (10 ** DECIMALS)
        return f"{val:,.2f} {DENOM_DISPLAY}"
    except (ValueError, TypeError):
        return amount_str


def raw_to_float(amount_str: str) -> float:
    try:
        return int(amount_str) / (10 ** DECIMALS)
    except (ValueError, TypeError):
        return 0.0


def http_get(url: str, timeout: int = 10) -> dict:
    """Minimal HTTP GET returning JSON. Requires urllib (stdlib)."""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  ⚠ HTTP {e.code} fetching {url}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"  ⚠ Error fetching {url}: {e}", file=sys.stderr)
        return {}


# ── Cosmos SDK LCD / RPC queries ────────────────────────────────────────────

def get_delegations(api: str, wallet: str) -> list[dict]:
    """Fetch all delegations for a wallet."""
    url = f"{api}/cosmos/staking/v1beta1/delegations/{wallet}"
    data = http_get(url)
    return data.get("delegation_responses", [])


def get_delegation_rewards(api: str, wallet: str, validator: str = "") -> list[dict]:
    """Fetch rewards. If validator given, fetch per-validator rewards."""
    if validator:
        url = f"{api}/cosmos/distribution/v1beta1/delegators/{wallet}/rewards/{validator}"
    else:
        url = f"{api}/cosmos/distribution/v1beta1/delegators/{wallet}/rewards"
    data = http_get(url)
    return data.get("rewards", [])


def get_validators(api: str) -> list[dict]:
    """Fetch all validators."""
    url = f"{api}/cosmos/staking/v1beta1/validators?pagination.limit=200"
    data = http_get(url)
    return data.get("validators", [])


def get_validator_info(api: str, valoper: str) -> dict:
    """Fetch single validator info."""
    url = f"{api}/cosmos/staking/v1beta1/validators/{valoper}"
    data = http_get(url)
    return data.get("validator", {})


# ── Core tracker ────────────────────────────────────────────────────────────

def track_wallet(api: str, wallet: str) -> list[dict]:
    """Track delegations and rewards for a single wallet."""
    print(f"\nFetching delegations for {wallet}...")

    delegations = get_delegations(api, wallet)
    all_rewards = get_delegation_rewards(api, wallet)

    # Index rewards by validator
    rewards_map: dict[str, float] = {}
    for r in all_rewards:
        val = r.get("validator_address", "")
        reward = 0.0
        for coin in r.get("reward", []):
            if coin.get("denom") == DENOM:
                reward += raw_to_float(coin.get("amount", "0"))
        rewards_map[val] = reward

    total_rewards = 0.0
    for coin in http_get(f"{api}/cosmos/distribution/v1beta1/delegators/{wallet}/rewards").get("total", []):
        if coin.get("denom") == DENOM:
            total_rewards += raw_to_float(coin.get("amount", "0"))

    results = []
    for d in delegations:
        delegation = d.get("delegation", {})
        valoper = delegation.get("validator_address", "unknown")
        delegated = raw_to_float(d.get("balance", {}).get("amount", "0"))
        rewards = rewards_map.get(valoper, 0.0)

        # Estimate APY (rough: rewards / delegated annualized)
        # In production you'd use inflation / commission data
        apy = (rewards / delegated * 100) if delegated > 0 else 0.0

        results.append({
            "validator": valoper,
            "delegated": delegated,
            "rewards": rewards,
            "apy": apy,
            "status": "Active",  # would check validator status in production
            "wallet": wallet,
        })

    return results


def print_table(results: list[dict]):
    """Print a formatted delegation table."""
    if not results:
        print("  No delegations found.")
        return

    print(f"\n{'='*60}")
    print(f"  RustChain Delegation Tracker")
    print(f"{'='*60}")

    total_delegated = 0.0
    total_rewards = 0.0
    wallet = results[0].get("wallet", "")
    print(f"  Wallet: {wallet}\n")

    print(f"  {'Validator':<40} {'Delegated':>12} {'Rewards':>12} {'APY':>7}")
    print(f"  {'-'*40} {'-'*12} {'-'*12} {'-'*7}")

    for r in results:
        val_short = r["validator"][:38] if len(r["validator"]) > 38 else r["validator"]
        print(f"  {val_short:<40} {r['delegated']:>12,.2f} {r['rewards']:>12,.4f} {r['apy']:>6.2f}%")
        total_delegated += r["delegated"]
        total_rewards += r["rewards"]

    portfolio_apy = (total_rewards / total_delegated * 100) if total_delegated > 0 else 0.0

    print(f"\n  Total Delegated: {total_delegated:,.2f} {DENOM_DISPLAY}")
    print(f"  Total Rewards:   {total_rewards:,.4f} {DENOM_DISPLAY}")
    print(f"  Portfolio APY:   {portfolio_apy:.2f}%")
    print()


# ── CSV Export ───────────────────────────────────────────────────────────────

def export_csv(results: list[dict], filepath: str, rewards_only: bool = False):
    """Export delegation data to CSV."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "wallet", "validator", "delegated_amount",
            "rewards_amount", "apy_percent", "status",
        ])
        now = datetime.now(timezone.utc).isoformat()
        for r in results:
            if rewards_only and r["rewards"] == 0:
                continue
            writer.writerow([
                now,
                r["wallet"],
                r["validator"],
                r["delegated"],
                r["rewards"],
                f"{r['apy']:.2f}",
                r["status"],
            ])

    print(f"  ✓ Exported {len(results)} records to {path}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RustChain Delegation Tracker")
    parser.add_argument("--wallet", "-w", help="Wallet address to track")
    parser.add_argument("--wallets", help="Comma-separated list of wallet addresses")
    parser.add_argument("--api", default=DEFAULT_API, help="LCD API endpoint")
    parser.add_argument("--export", help="Export to CSV file path")
    parser.add_argument("--export-rewards", help="Export rewards-only to CSV")
    parser.add_argument("--watch", type=int, help="Auto-refresh interval in seconds")
    args = parser.parse_args()

    wallets = []
    if args.wallets:
        wallets = [w.strip() for w in args.wallets.split(",")]
    if args.wallet:
        wallets.append(args.wallet)

    if not wallets:
        parser.error("Provide --wallet or --wallets")

    while True:
        all_results = []
        for wallet in wallets:
            results = track_wallet(args.api, wallet)
            all_results.extend(results)
            print_table(results)

        if args.export:
            export_csv(all_results, args.export)
        if args.export_rewards:
            export_csv(all_results, args.export_rewards, rewards_only=True)

        if not args.watch:
            break

        print(f"  Refreshing in {args.watch}s... (Ctrl+C to stop)")
        try:
            time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n  Stopped.")
            break


if __name__ == "__main__":
    main()
