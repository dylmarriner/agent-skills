# Monero Wallet Generation via Official CLI

## Why the Official CLI

The Monero CLI binary (monero-wallet-cli) embeds the canonical wordlist for each language. GitHub source code wordlists may differ from the release binary's wordlist, causing "Electrum-style word list failed verification" errors when restoring. Always use the release binary.

## Full Wallet Generation Script

```bash
#!/bin/bash
# generate-monero-wallet.sh - Creates a new Monero wallet with a valid seed

MONERO_URL="https://downloads.getmonero.org/cli/linux64"
WALLET_NAME="${1:-monero-wallet}"
WALLET_PASS="${2:-mywalletpass}"
WORKDIR="/tmp/monero-wallet-gen"
OUTDIR="$HOME/.feather/wallets"

# Download CLI if not cached
if [ ! -d "$WORKDIR/monero-bin" ]; then
    mkdir -p "$WORKDIR"
    cd "$WORKDIR"
    echo "Downloading Monero CLI (80MB)..."
    curl -sL "$MONERO_URL" -o monero-cli.tar.bz2
    tar -xjf monero-cli.tar.bz2
    mv monero-x86_64-linux-gnu-* monero-bin
fi

# Create password file
echo -n "$WALLET_PASS" > "$WORKDIR/pw.txt"

# Generate wallet using expect (handles interactive language prompt)
expect << EXPECTEOF
set timeout 30
spawn "$WORKDIR/monero-bin/monero-wallet-cli" \
    --generate-new-wallet="$WORKDIR/$WALLET_NAME" \
    --password-file="$WORKDIR/pw.txt" \
    --log-level=0
expect "language of your choice:" { send "1\r" }
expect eof
EXPECTEOF

# Extract seed from log
echo "Wallet generated at: $WORKDIR/$WALLET_NAME"
echo "Keys at: $WORKDIR/$WALLET_NAME.keys"
echo "Password: $WALLET_PASS"

# Copy to Feather wallets directory
mkdir -p "$OUTDIR"
cp "$WORKDIR/$WALLET_NAME" "$WORKDIR/$WALLET_NAME".keys "$WORKDIR/$WALLET_NAME".address "$OUTDIR/" 2>/dev/null
echo "Copied to $OUTDIR/"

# Show seed (from monero-wallet-cli.log)
grep -A1 "NOTE: the following" "$WORKDIR/monero-bin/monero-wallet-cli.log" | tail -5
```

## Key Points

1. **Language selection**: The wallet CLI prompts for language even with `--use-english-language-names`. Always match on "language of your choice:" and send "1\r".
2. **Password file**: Use `--password-file` to avoid the password prompt.
3. **No daemon needed**: Wallet generation works offline. Skip `--daemon-address` for pure key generation.
4. **Seed extraction**: The seed appears in stdout after generation, preceded by "NOTE: the following 25 words".
5. **Wallet files**: Three files created: `<name>` (wallet cache), `<name>.keys` (encrypted keys), `<name>.address` (public address).
6. **Feather compatibility**: Monero CLI wallets are directly loadable by Feather via "Open wallet from file" or by placing them in `~/.feather/wallets/`.
