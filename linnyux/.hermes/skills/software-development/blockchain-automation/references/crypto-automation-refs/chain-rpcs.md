# Chain RPC Endpoints — Failover Pools

## Ethereum (ETH)
**Chain ID:** 1
**Explorer:** https://etherscan.io

```python
ETH_RPC_POOL = [
    "https://eth.drpc.org",
    "https://rpc.ankr.com/eth",
    "https://cloudflare-eth.com",
    "https://eth-mainnet.public.blastapi.io",
    "https://ethereum-rpc.publicnode.com",
    "https://1rpc.io/eth",
    "https://eth.llamarpc.com",
]
```

**WebSocket (MEV/Mempool):** wss://eth.drpc.org, wss://ethereum-rpc.publicnode.com, wss://rpc.ankr.com/eth/ws

**Gas:** ~0.3-50 gwei. Cheapest on weekends, early UTC mornings.

## BSC (BNB Smart Chain)
**Chain ID:** 56
**Explorer:** https://bscscan.com

```python
BSC_RPC_POOL = [
    "https://bsc-dataseed1.binance.org",
    "https://bsc-dataseed2.binance.org",
    "https://bsc-dataseed3.binance.org",
    "https://bsc-dataseed4.binance.org",
    "https://bsc-rpc.publicnode.com",
    "https://rpc.ankr.com/bsc",
]
```

**Gas:** ~0.05-5 gwei. ~10x cheaper than ETH.

## Bitcoin (BTC)
**No RPC — uses REST APIs**
**Explorer:** https://mempool.space

```python
BTC_API_POOL = [
    "https://mempool.space/api",
    "https://blockstream.info/api",
    "https://btc.parserpeer.com/api",
]
```

**Fee estimate:** GET /v1/fees/recommended
**UTXOs:** GET /address/{addr}/utxo

## Solana (SOL)
**Chain ID:** 501 (not EVM)
**Explorer:** https://solscan.io

```python
SOL_RPC_POOL = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com",
    "https://rpc.ankr.com/solana",
    "https://solana.llama.rpc.com",
]
```

**Key difference:** Ed25519 curve (not secp256k1). Requires `solders` + `solana-py` packages.
**SPL tokens:** Use `getTokenAccountsByOwner` RPC method.

## Dogecoin (DOGE)
**No RPC — uses REST APIs**
**Explorer:** https://dogechain.info

```python
DOGE_API_POOL = [
    "https://api.blockcypher.com/v1/doge/main",
    "https://api.blockchair.com/dogecoin/dashboards/address/{addr}",
]
```

## L2 Networks

| Chain | RPC | Chain ID | Notes |
|-------|-----|----------|-------|
| Arbitrum | https://arb1.arbitrum.io/rpc | 42161 | 7-day bridge delay |
| Base | https://mainnet.base.org | 8453 | Coinbase L2 |
| Optimism | https://mainnet.optimism.io | 10 | 7-day challenge period |
| Polygon | https://polygon-rpc.com | 137 | Cheap, fast finality |

## Aave V3 Pool Providers (Flash Loans)

| Chain | Address Provider |
|-------|-----------------|
| ETH | 0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e |
| BSC | 0xff75B6da14Ff3fD6F2b5BD5eC132C9fB93E8A461 |
| Polygon | 0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb |
| Arbitrum | 0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb |
| Optimism | 0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb |
| Base | 0xe20fCBdBfFC4Dd138cE8b2E6FA3F7b91B6f8F7C3 |
