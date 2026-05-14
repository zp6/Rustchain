#!/usr/bin/env python3
"""RustChain Epoch Calculator — calculate epoch times, predict rewards."""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta

# ── Config ──────────────────────────────────────────────────────────────────

DEFAULT_RPC = os.getenv("RUSTCHAIN_RPC", "https://rpc.rustchain.io")
EPOCH_BLOCKS = int(os.getenv("EPOCH_BLOCKS", "100"))
BLOCK_TIME = int(os.getenv("BLOCK_TIME", "6"))  # seconds
CHAIN_DENOM = os.getenv("RUSTCHAIN_DENOM", "RUST")
CHAIN_ID = os.getenv("RUSTCHAIN_CHAIN_ID", "rustchain-1")

# ── Helpers ─────────────────────────────────────────────────────────────────

def http_get(url: str, timeout: int = 10) -> dict:
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"⚠ Error fetching {url}: {e}", file=sys.stderr)
        return {}


def get_status(rpc: str) -> dict:
    """Get node status including latest block."""
    return http_get(f"{rpc}/status")


def get_staking_params(api_base: str) -> dict:
    """Fetch staking module params."""
    # Try LCD-style endpoint
    data = http_get(f"{api_base}/cosmos/staking/v1beta1/params")
    return data.get("params", {})


def get_latest_block(rpc: str) -> tuple[int, datetime]:
    """Get latest block height and time."""
    status = get_status(rpc)
    sync_info = status.get("result", {}).get("sync_info", {})
    height = int(sync_info.get("latest_block_height", "0"))
    time_str = sync_info.get("latest_block_time", "")
    try:
        block_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        block_time = datetime.now(timezone.utc)
    return height, block_time


# ── Epoch calculations ──────────────────────────────────────────────────────

def block_to_epoch(height: int) -> int:
    """Convert block height to epoch number."""
    return height // EPOCH_BLOCKS


def epoch_to_block(epoch: int) -> int:
    """Get starting block height for an epoch."""
    return epoch * EPOCH_BLOCKS


def epoch_progress(height: int) -> float:
    """Get progress within current epoch (0.0 - 1.0)."""
    return (height % EPOCH_BLOCKS) / EPOCH_BLOCKS


def time_to_next_epoch(height: int) -> timedelta:
    """Estimate time remaining until next epoch."""
    remaining_blocks = EPOCH_BLOCKS - (height % EPOCH_BLOCKS)
    return timedelta(seconds=remaining_blocks * BLOCK_TIME)


def print_current_epoch(rpc: str):
    """Display current epoch information."""
    height, block_time = get_latest_block(rpc)

    epoch = block_to_epoch(height)
    progress = epoch_progress(height)
    remaining = time_to_next_epoch(height)
    elapsed_blocks = height % EPOCH_BLOCKS
    next_epoch_block = epoch_to_block(epoch + 1)
    next_epoch_time = block_time + remaining

    print(f"\n{'='*50}")
    print(f"  RustChain Epoch Calculator")
    print(f"{'='*50}")
    print(f"  Current Block:    {height:,}")
    print(f"  Blocks Per Epoch: {EPOCH_BLOCKS}")
    print(f"  Current Epoch:    {epoch:,}")
    print(f"  Epoch Progress:   {progress*100:.1f}% (block {elapsed_blocks}/{EPOCH_BLOCKS})")
    print(f"")
    print(f"  Time in Epoch:    {_fmt_elapsed(elapsed_blocks * BLOCK_TIME)}")
    print(f"  Time Remaining:   {_fmt_delta(remaining)}")
    print(f"  Next Epoch At:    {next_epoch_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  Next Epoch Block: {next_epoch_block:,}")
    print()


def project_rewards(rpc: str, num_epochs: int, delegated: float,
                    commission: float = 0.0, inflation: float = 0.10,
                    bonded_ratio: float = 0.50):
    """Project estimated rewards over multiple epochs.

    Simplified model: reward_per_epoch = (delegated / total_supply) * inflation_per_epoch
    Adjusted for validator commission.
    """
    height, block_time = get_latest_block(rpc)
    current_epoch = block_to_epoch(height)

    # Rough estimation: annual reward rate
    # annual_reward_rate = inflation * (1 - community_tax) / bonded_ratio
    community_tax = 0.02  # typical 2%
    annual_rate = inflation * (1 - community_tax) / bonded_ratio if bonded_ratio > 0 else 0

    # Epochs per year (rough)
    epochs_per_year = (365.25 * 24 * 3600) / (EPOCH_BLOCKS * BLOCK_TIME)
    epoch_rate = annual_rate / epochs_per_year

    # After commission
    net_rate = epoch_rate * (1 - commission)

    print(f"\n{'='*60}")
    print(f"  Reward Projection ({num_epochs} epochs)")
    print(f"{'='*60}")
    print(f"  Delegated: {delegated:,.2f} {CHAIN_DENOM}")
    print(f"  Commission: {commission*100:.1f}%")
    print(f"  Est. Annual Rate: {annual_rate*100:.2f}%")
    print(f"  Epochs/Year: ~{epochs_per_year:.1f}")
    print()

    print(f"  {'Epoch':<10} {'Block':<14} {'Est. Reward':>15} {'Cumulative':>15}")
    print(f"  {'-'*10} {'-'*14} {'-'*15} {'-'*15}")

    cumulative = 0.0
    for i in range(1, num_epochs + 1):
        epoch_num = current_epoch + i
        reward = delegated * net_rate
        cumulative += reward

        block_start = epoch_to_block(epoch_num)
        print(f"  {epoch_num:<10,} {block_start:<14,} {reward:>12,.4f} {CHAIN_DENOM:>3} {cumulative:>12,.4f} {CHAIN_DENOM:>3}")

    print(f"\n  Total projected ({num_epochs} epochs): {cumulative:,.4f} {CHAIN_DENOM}")
    annual_equiv = cumulative * (epochs_per_year / num_epochs) if num_epochs > 0 else 0
    print(f"  Annual equivalent: {annual_equiv:,.4f} {CHAIN_DENOM}")
    print()


def convert_block_to_epoch(height: int):
    """Convert a block height to epoch info."""
    epoch = block_to_epoch(height)
    start = epoch_to_block(epoch)
    end = start + EPOCH_BLOCKS - 1
    print(f"  Block {height:,} → Epoch {epoch:,}")
    print(f"  Epoch range: blocks {start:,} – {end:,}")
    print(f"  Position in epoch: block {height - start}/{EPOCH_BLOCKS}")


def convert_epoch_to_block(epoch: int):
    """Convert epoch number to block range."""
    start = epoch_to_block(epoch)
    end = start + EPOCH_BLOCKS - 1
    est_time = timedelta(seconds=start * BLOCK_TIME)
    print(f"  Epoch {epoch:,} → blocks {start:,} – {end:,}")
    print(f"  Est. start time offset from genesis: {_fmt_delta(est_time)}")


def _fmt_delta(td: timedelta) -> str:
    total = int(td.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _fmt_elapsed(seconds: int) -> str:
    return _fmt_delta(timedelta(seconds=seconds))


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RustChain Epoch Calculator")
    parser.add_argument("--rpc", default=DEFAULT_RPC, help="RPC endpoint")
    parser.add_argument("--project", type=int, metavar="N",
                        help="Project rewards for N epochs")
    parser.add_argument("--delegated", type=float, default=10000,
                        help="Delegated amount for projection (default: 10000)")
    parser.add_argument("--commission", type=float, default=0.0,
                        help="Validator commission rate (default: 0.0)")
    parser.add_argument("--inflation", type=float, default=0.10,
                        help="Annual inflation rate (default: 0.10)")
    parser.add_argument("--bonded-ratio", type=float, default=0.50,
                        help="Bonded ratio (default: 0.50)")
    parser.add_argument("--block-to-epoch", type=int, metavar="HEIGHT",
                        help="Convert block height to epoch")
    parser.add_argument("--epoch-to-block", type=int, metavar="EPOCH",
                        help="Convert epoch to block height")
    args = parser.parse_args()

    if args.block_to_epoch:
        convert_block_to_epoch(args.block_to_epoch)
    elif args.epoch_to_block is not None:
        convert_epoch_to_block(args.epoch_to_block)
    elif args.project:
        project_rewards(args.rpc, args.project, args.delegated,
                        args.commission, args.inflation, args.bonded_ratio)
    else:
        print_current_epoch(args.rpc)


if __name__ == "__main__":
    main()
