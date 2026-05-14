# Developer Quickstart for RustChain

One-command setup for RustChain development environment. Get from zero to building in minutes.

## Features

- **One-command setup** — Install all dependencies and configure environment
- **Cross-platform** — Bash (Linux/macOS) and Python (any OS) versions
- **Auto-configuration** — Generate keys, configure node, set up networking
- **Verification** — Automatically verify all components are working
- **Development mode** — Local testnet with faucet for development

## Quick Start

### Bash (Linux/macOS)
```bash
chmod +x quickstart.sh
./quickstart.sh
```

### Python (any OS)
```bash
python quickstart.py
```

## What It Sets Up

1. **System dependencies** — Go, Rust, build tools
2. **RustChain binary** — Compile from source or download release
3. **Local testnet** — Single-node devnet with pre-funded accounts
4. **CLI configuration** — Set up `rustchaind` with default keyring
5. **Faucet account** — Pre-funded dev wallet for testing
6. **Development tools** — Helpful aliases and scripts

## Options

```bash
# Full setup (default)
./quickstart.sh --full

# Minimal setup (binary + config only)
./quickstart.sh --minimal

# Skip compilation, download binary
./quickstart.sh --download

# Custom chain ID
./quickstart.sh --chain-id my-testnet

# With monitoring
./quickstart.sh --with-monitoring
```

## Post-Setup

After running quickstart, you'll have:

```
~/.rustchain/
├── config/          # Node configuration
├── data/            # Blockchain data
├── keyring-test/    # Development keys
└── scripts/         # Helper scripts
```

Useful commands:
```bash
# Check node status
rustchaind status

# Query balance
rustchaind query bank balances zp6

# Send tokens
rustchaind tx bank send <from> <to> 1000urst --yes

# List validators
rustchaind query staking validators
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | `./quickstart.sh --reset` |
| Build fails | Install Go 1.21+ and Rust 1.70+ |
| Keyring issues | `rustchaind keys list --keyring-backend test` |

## License

MIT
