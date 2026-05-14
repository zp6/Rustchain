#!/usr/bin/env python3
"""RustChain Health Checker — monitor node health with multi-node support and alerting."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────

DEFAULT_RPC = os.getenv("RUSTCHAIN_RPC", "http://localhost:26657")
DEFAULT_MIN_PEERS = int(os.getenv("HEALTH_MIN_PEERS", "5"))
DEFAULT_MAX_LAG = int(os.getenv("HEALTH_MAX_LAG", "100"))

# ── Helpers ─────────────────────────────────────────────────────────────────

def http_get(url: str, timeout: int = 10) -> dict:
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"_error": str(e)}


def http_post(url: str, payload: dict, timeout: int = 10) -> bool:
    """Send a webhook notification."""
    import urllib.request
    import urllib.error
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception as e:
        print(f"  ⚠ Webhook failed: {e}", file=sys.stderr)
        return False


# ── Node health check ───────────────────────────────────────────────────────

class HealthStatus:
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    DOWN = "DOWN"


def check_node(name: str, rpc: str, api: str = "", min_peers: int = DEFAULT_MIN_PEERS,
               max_lag: int = DEFAULT_MAX_LAG, reference_height: int = 0) -> dict:
    """Check a single node's health."""
    result = {
        "name": name,
        "rpc": rpc,
        "status": HealthStatus.HEALTHY,
        "synced": False,
        "height": 0,
        "peers": 0,
        "voting_power": 0,
        "lag": 0,
        "errors": [],
    }

    # Get node status
    status_data = http_get(f"{rpc}/status")
    if "_error" in status_data:
        result["status"] = HealthStatus.DOWN
        result["errors"].append(f"RPC unreachable: {status_data['_error']}")
        return result

    sync_info = status_data.get("result", {}).get("sync_info", {})
    node_info = status_data.get("result", {}).get("node_info", {})

    result["synced"] = not sync_info.get("catching_up", True)
    result["height"] = int(sync_info.get("latest_block_height", "0"))
    result["peers"] = int(status_data.get("result", {}).get("peers", {}).get("count", "0") or
                          len(status_data.get("result", {}).get("peers", {}).get("peers", [])))

    # Voting power from node_info
    voting_power = node_info.get("default_peer_id", "")
    validator_info = status_data.get("result", {}).get("validator_info", {})
    result["voting_power"] = int(validator_info.get("voting_power", "0"))

    # Check for issues
    if not result["synced"]:
        result["status"] = HealthStatus.CRITICAL
        result["errors"].append("Node is catching up (not synced)")

    # Block lag check
    if reference_height > 0:
        result["lag"] = reference_height - result["height"]
        if result["lag"] > max_lag:
            result["status"] = HealthStatus.WARNING if result["status"] == HealthStatus.HEALTHY else result["status"]
            result["errors"].append(f"Block lag: {result['lag']} blocks behind")

    # Peer count check
    if result["peers"] < min_peers:
        if result["status"] == HealthStatus.HEALTHY:
            result["status"] = HealthStatus.WARNING
        result["errors"].append(f"Low peer count: {result['peers']} (min: {min_peers})")

    # Check consensus if API available
    if api:
        consensus = http_get(f"{rpc}/consensus_state")
        # Could add more checks here

    return result


def print_health(results: list[dict]):
    """Print a formatted health report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n{'='*60}")
    print(f"  RustChain Health Check")
    print(f"  Time: {now}")
    print(f"{'='*60}")

    status_icons = {
        HealthStatus.HEALTHY: "✅",
        HealthStatus.WARNING: "⚠",
        HealthStatus.CRITICAL: "🔴",
        HealthStatus.DOWN: "💀",
    }

    healthy = warning = critical = down = 0

    for r in results:
        icon = status_icons.get(r["status"], "?")
        print(f"\n  Node: {r['name']} ({r['rpc']})")
        print(f"    Status:    {icon} {r['status']}")
        print(f"    Synced:    {'Yes' if r['synced'] else 'No'}")
        print(f"    Height:    {r['height']:,}")
        print(f"    Peers:     {r['peers']}")
        if r["voting_power"]:
            print(f"    Vote Power: {r['voting_power']}")
        if r["lag"]:
            print(f"    Lag:       {r['lag']} blocks")
        if r["errors"]:
            for err in r["errors"]:
                print(f"    ⚠ {err}")

        if r["status"] == HealthStatus.HEALTHY:
            healthy += 1
        elif r["status"] == HealthStatus.WARNING:
            warning += 1
        elif r["status"] == HealthStatus.CRITICAL:
            critical += 1
        else:
            down += 1

    print(f"\n  Summary: {healthy} healthy, {warning} warning, {critical} critical, {down} down")
    print()


def send_alert(results: list[dict], webhook: str):
    """Send alert for unhealthy nodes via webhook."""
    unhealthy = [r for r in results if r["status"] != HealthStatus.HEALTHY]
    if not unhealthy:
        return

    # Detect webhook type
    is_slack = "slack.com" in webhook
    is_discord = "discord.com" in webhook

    lines = []
    for r in unhealthy:
        lines.append(f"**{r['name']}** ({r['rpc']}): {r['status']}")
        for err in r["errors"]:
            lines.append(f"  - {err}")

    text = "\n".join(lines)

    if is_slack:
        payload = {
            "text": "⚠ RustChain Node Alert",
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": text}}],
        }
    elif is_discord:
        payload = {"content": f"⚠ **RustChain Node Alert**\n{text}"}
    else:
        payload = {"alert": "RustChain Node Alert", "nodes": unhealthy}

    success = http_post(webhook, payload)
    if success:
        print(f"  📤 Alert sent to webhook ({len(unhealthy)} unhealthy nodes)")


# ── Node config loading ─────────────────────────────────────────────────────

def load_nodes(filepath: str) -> list[dict]:
    """Load node configurations from JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RustChain Health Checker")
    parser.add_argument("--node", help="Single node RPC endpoint")
    parser.add_argument("--nodes", help="JSON file with node configurations")
    parser.add_argument("--min-peers", type=int, default=DEFAULT_MIN_PEERS,
                        help=f"Minimum peer count threshold (default: {DEFAULT_MIN_PEERS})")
    parser.add_argument("--max-lag", type=int, default=DEFAULT_MAX_LAG,
                        help=f"Maximum block lag threshold (default: {DEFAULT_MAX_LAG})")
    parser.add_argument("--interval", type=int, help="Check interval in seconds (daemon mode)")
    parser.add_argument("--webhook", help="Webhook URL for alert notifications")
    args = parser.parse_args()

    # Build node list
    nodes = []
    if args.nodes:
        nodes = load_nodes(args.nodes)
    if args.node:
        nodes.append({"name": "default", "rpc": args.node})

    if not nodes:
        nodes.append({"name": "local", "rpc": DEFAULT_RPC})

    while True:
        # First pass: get reference height (max height among all nodes)
        heights = []
        for n in nodes:
            data = http_get(f"{n['rpc']}/status")
            if "_error" not in data:
                h = int(data.get("result", {}).get("sync_info", {}).get("latest_block_height", "0"))
                heights.append(h)
        reference = max(heights) if heights else 0

        # Second pass: check each node
        results = []
        for n in nodes:
            r = check_node(
                name=n.get("name", n["rpc"]),
                rpc=n["rpc"],
                api=n.get("api", ""),
                min_peers=args.min_peers,
                max_lag=args.max_lag,
                reference_height=reference,
            )
            results.append(r)

        print_health(results)

        if args.webhook:
            send_alert(results, args.webhook)

        if not args.interval:
            break

        print(f"  Next check in {args.interval}s... (Ctrl+C to stop)")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n  Stopped.")
            break


if __name__ == "__main__":
    main()
