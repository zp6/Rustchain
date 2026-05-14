# Health Checker for RustChain

Monitor RustChain node health with multi-node support, alerting, and periodic checks.

## Features

- **Node health monitoring** — Check sync status, peer count, block height, voting power
- **Multi-node support** — Monitor multiple nodes from a single instance
- **Alert notifications** — Webhook-based alerts when nodes go unhealthy
- **Periodic checks** — Run as a daemon with configurable intervals
- **Health report** — Summary of all monitored nodes

## Quick Start

```bash
# Check a single node
python check.py --node https://rpc.rustchain.io:26657

# Check multiple nodes
python check.py --nodes node1.json
```

## Usage

### Single Node Check
```bash
python check.py --node http://localhost:26657
```

### Multi-Node Configuration
Create a `nodes.json` file:

```json
[
  {
    "name": "validator-1",
    "rpc": "http://localhost:26657",
    "api": "http://localhost:1317"
  },
  {
    "name": "sentry-1",
    "rpc": "http://sentry1.example.com:26657"
  }
]
```

```bash
python check.py --nodes nodes.json
```

### Periodic Monitoring
```bash
# Check every 60 seconds
python check.py --nodes nodes.json --interval 60

# With webhook alerting
python check.py --nodes nodes.json --interval 60 --webhook https://hooks.slack.com/xxx
```

### Alert Thresholds
```bash
# Alert if peer count below 5 or block lag > 100
python check.py --nodes nodes.json --min-peers 5 --max-lag 100 --webhook URL
```

## Alert Configuration

Supports webhook notifications (Slack, Discord, custom):
```bash
--webhook https://hooks.slack.com/services/XXX
--webhook https://discord.com/api/webhooks/XXX
```

## Output Example

```
=== RustChain Health Check ===
Time: 2026-05-15 03:20:00 UTC

Node: validator-1 (http://localhost:26657)
  Status:    ✅ HEALTHY
  Synced:    Yes
  Height:    1,234,567
  Peers:     42
  Vote Power: 100

Node: sentry-1 (http://sentry1.example.com:26657)
  Status:    ⚠ WARNING
  Synced:    Yes
  Height:    1,234,500
  Peers:     3 (low!)
  Lag:       67 blocks

Summary: 1 healthy, 1 warning, 0 critical
```

## License

MIT
