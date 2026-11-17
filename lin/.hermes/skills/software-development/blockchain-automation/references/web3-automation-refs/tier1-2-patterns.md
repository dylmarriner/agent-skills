# Tier 1 & 2 Patterns — Multi-Chain Crypto Automation

## RPC Endpoints

### Ethereum (failover pool)
```
https://eth.drpc.org
https://rpc.ankr.com/eth
https://cloudflare-eth.com
https://eth-mainnet.public.blastapi.io
https://ethereum-rpc.publicnode.com
https://1rpc.io/eth
https://eth.llamarpc.com
```

### BSC (failover pool)
```
https://bsc-dataseed1.binance.org
https://bsc-dataseed2.binance.org
https://bsc-dataseed3.binance.org
https://bsc-dataseed4.binance.org
https://bsc-rpc.publicnode.com
https://rpc.ankr.com/bsc
```

### Solana (failover pool)
```
https://api.mainnet-beta.solana.com
https://solana-rpc.publicnode.com
https://rpc.ankr.com/solana
https://solana.llama.rpc.com
```

### BTC (REST APIs)
```
https://mempool.space/api       — address balance, UTXOs, fee estimates
https://blockstream.info/api     — same endpoints, backup
```

### DOGE
```
https://api.blockcypher.com/v1/doge/main  — balance, address info
https://api.blockchair.com/dogecoin        — fallback (rate limited)
```

## DEX Router Addresses

| Router | Address (Ethereum) |
|--------|-------------------|
| Uniswap V2 | `0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D` |
| Uniswap V3 | `0xE592427A0AEce92De3Edee1F18E0157C05861564` |
| PancakeSwap V2 | `0x10ED43C718714eb63d5aA57B78B54704E256024E` |
| PancakeSwap V3 | `0x13f4EA83D0bd40E75C8222255bc855a974568Dd4` |
| 0x Exchange | `0xdef1c0ded9bec7f1a1670819833240f027b25eff` |
| 1inch V5 | `0x1111111254fb6c44bac0bed2854e76f90643097d` |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` |

## Aave V3 Pool Address Providers

| Chain | Address |
|-------|---------|
| Ethereum | `0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e` |
| BSC | `0xff75B6da14Ff3fD6F2b5BD5eC132C9fB93E8A461` |
| Polygon | `0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb` |
| Arbitrum | `0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb` |
| Optimism | `0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb` |
| Base | `0xe20fCBdBfFC4Dd138cE8b2E6FA3F7b91B6f8F7C3` |

## Wrapped Native Tokens

| Chain | Token | Address |
|-------|-------|---------|
| Ethereum | WETH | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` |
| BSC | WBNB | `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` |

## Uniswap V2 Swap Function Signatures

```
swapExactTokensForETH:                  0x18cbafe5
swapExactETHForTokens:                  0x7ff36ab5
swapExactTokensForTokens:               0x38ed1739
swapTokensForExactETH:                  0x4a25d94a
swapTokensForExactTokens:               0x5c11d795
swapExactTokensForETHSupportingFeeOnTransferTokens: 0x791ac947
addLiquidity:                           0xe8e33700
addLiquidityETH:                        0xf305d719
```

## Top NFT Collections (ERC721)

| Collection | Contract |
|------------|----------|
| BoredApeYachtClub | `0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D` |
| CryptoPunks | `0xb47e3cd837dDF8e4c57F05d70Ab865de6e193BBB` |
| MutantApeYachtClub | `0x60E4d786628Fea6478F785A6d7e704777c86a7c6` |
| Azuki | `0xED5AF388653567Af2F388E6224dC7C4b3241C544` |
| CloneX | `0x49cF6f5d44E70224e2E23fDcdd2C053F30aDA28B` |
| Doodles | `0x8a90CAb2b38dba80c64b7734e58Ee1dB38B8992e` |
| PudgyPenguins | `0xBd3531dA5CF5857e7CfAA92426877b022e612cf8` |
| Milady | `0x5Af0D9827E0c53E4799BB226655A1de152A425a5` |

## Pipewire dependency note

When `pip install` fails with `externally-managed-environment` (PEP 668), create a venv:
```bash
python3 -m venv venv
./venv/bin/pip install <packages>
```
Use `./venv/bin/python3` to run scripts that need the new deps. The system python outside venv will still have web3, ecdsa, etc.

## SPL Token RPC Query

Solana token accounts:
```json
{
  "jsonrpc": "2.0",
  "method": "getTokenAccountsByOwner",
  "params": [
    "<owner_address>",
    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
    {"encoding": "jsonParsed"}
  ]
}
```

## Critical Packages

```txt
web3>=6.0.0        — EVM chain interaction
mnemonic>=0.21     — BIP39 validation
bip-utils>=2.12.1  — BIP44 derivation paths
solders>=0.27.1    — Solana Keypair/Pubkey types
solana>=0.36.12    — Solana RPC Client
ecdsa>=0.18.0      — SECP256k1 operations
base58>=2.1.0      — BTC address encoding
python-telegram-bot>=22.0 — C2 bot
stem>=1.8.0        — Tor controller (circuit rotation)
```
