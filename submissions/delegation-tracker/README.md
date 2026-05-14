# Delegation Tracker for RustChain

Track your RustChain delegation status, rewards, and performance in real-time.

## Features

- **Real-time tracking** — Monitor delegation status across multiple validators
- **Reward calculation** — Track earned rewards with compound growth
- **CSV export** — Export delegation history for accounting/tax purposes
- **Multi-validator support** — Track delegations to multiple validators simultaneously
- **Historical data** — Keep records of all delegation changes

## Quick Start

```bash
python tracker.py --wallet zp6
```

## Usage

### Basic Tracking
```bash
# Track delegations for a wallet
python tracker.py --wallet <ADDRESS>

# Track with auto-refresh every 60 seconds
python tracker.py --wallet <ADDRESS> --watch 60
```

### CSV Export
```bash
# Export all delegation history
python tracker.py --wallet <ADDRESS> --export delegations.csv

# Export rewards only
python tracker.py --wallet <ADDRESS> --export-rewards rewards.csv
```

### Multi-wallet
```bash
# Track multiple wallets
python tracker.py --wallets wallet1,wallet2,wallet3
```

## Configuration

Set environment variables or use a .env file:

```env
RUSTCHAIN_RPC=https://rpc.rustchain.io
RUSTCHAIN_API=https://api.rustchain.io
WALLET_ADDRESS=zp6
```

## Output Example

```
=== RustChain Delegation Tracker ===
Wallet: zp6

Validator          | Delegated    | Rewards     | APY    | Status
-------------------|-------------|-------------|--------|--------
rustvaloper1abc... | 10,000 RUST | 1,250 RUST  | 12.5%  | Active
rustvaloper1def... | 5,000 RUST  | 600 RUST    | 12.0%  | Active

Total Delegated: 15,000 RUST
Total Rewards:   1,850 RUST
Portfolio APY:   12.33%
```

## License

MIT
