# Epoch Calculator for RustChain

Calculate epoch times, predict next epochs, and estimate rewards for RustChain validators and delegators.

## Features

- **Epoch timing** — Calculate current epoch and time to next epoch
- **Reward estimation** — Predict rewards based on staking parameters
- **Multi-epoch projection** — Forecast rewards over multiple epochs
- **Block height mapping** — Convert between block height and epoch number

## Quick Start

```bash
python calc.py
```

## Usage

### Current Epoch Info
```bash
# Show current epoch status
python calc.py

# Custom RPC endpoint
python calc.py --rpc https://rpc.rustchain.io
```

### Reward Projection
```bash
# Project rewards for 10 epochs
python calc.py --project 10 --delegated 10000

# With validator commission
python calc.py --project 30 --delegated 50000 --commission 0.10
```

### Block ↔ Epoch Conversion
```bash
# Block height to epoch
python calc.py --block-to-epoch 1234567

# Epoch to block height
python calc.py --epoch-to-block 42
```

## Configuration

```env
RUSTCHAIN_RPC=https://rpc.rustchain.io
EPOCH_BLOCKS=100        # blocks per epoch (adjust per chain)
BLOCK_TIME=6            # seconds per block
CHAIN_DENOM=RUST
```

## Output Example

```
=== RustChain Epoch Calculator ===

Current Block:    1,234,567
Blocks Per Epoch: 100
Current Epoch:    12,345
Epoch Progress:   67% (block 67/100)

Time in Epoch:    6m 42s
Time Remaining:   3m 18s
Next Epoch At:    2026-05-15 03:25:00 UTC

--- Reward Projection (10 epochs) ---
Epoch     | Block       | Est. Reward  | Cumulative
----------|-------------|-------------|------------
12,346    | 1,234,600   | 12.50 RUST  | 12.50
12,347    | 1,234,700   | 12.50 RUST  | 25.00
...
```

## License

MIT
