# EVM Endpoints, Contract Addresses & Known Routers

## Reliable Public RPC Pools

### Ethereum (ETH)
```
https://eth.drpc.org
https://rpc.ankr.com/eth
https://cloudflare-eth.com
https://eth-mainnet.public.blastapi.io
https://ethereum-rpc.publicnode.com
https://1rpc.io/eth
https://eth.llamarpc.com
```

### BSC
```
https://bsc-dataseed1.binance.org
https://bsc-dataseed2.binance.org
https://bsc-dataseed3.binance.org
https://bsc-rpc.publicnode.com
https://rpc.ankr.com/bsc
```

### Solana
```
https://api.mainnet-beta.solana.com
https://solana-rpc.publicnode.com
https://rpc.ankr.com/solana
https://solana.llama.rpc.com
```

### Ethereum WebSocket (for mempool)
```
wss://eth.drpc.org
wss://ethereum-rpc.publicnode.com
wss://rpc.ankr.com/eth/ws
```

## DEX Router Addresses

### Uniswap V2 Router
`0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D`

### Uniswap V3 Router
`0xE592427A0AEce92De3Edee1F18E0157C05861564`

### Uniswap V3 Router (Alternate)
`0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45`

### PancakeSwap V2
`0x10ED43C718714eb63d5aA57B78B54704E256024E`

### PancakeSwap V3
`0x13f4EA83D0bd40E75C8222255bc855a974568Dd4`

### 0x Exchange Proxy
`0xdef1c0ded9bec7f1a1670819833240f027b25eff`

### 1inch V5 Router
`0x1111111254fb6c44bac0bed2854e76f90643097d`

### MetaSwap
`0x881d40237659c251811cec9c364ef91dc08d300c`

### WETH
`0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2`

### WBNB
`0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c`

## DEX Function Signatures (4-byte selectors)

| Function | Selector |
|----------|----------|
| swapExactTokensForTokens | `0x38ed1739` |
| swapExactETHForTokens | `0x7ff36ab5` |
| swapExactTokensForETH | `0x18cbafe5` |
| swapTokensForExactTokens | `0x4a25d94a` |
| swapTokensForExactETH | `0x4a25d94a` |
| swapExactTokensForETHSupportingFeeOnTransferTokens | `0x791ac947` |
| addLiquidity | `0xe8e33700` |
| addLiquidityETH | `0xf305d719` |

## Aave V3 Pool Address Providers

| Chain | Provider Address |
|-------|-----------------|
| Ethereum | `0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e` |
| BSC | `0xff75B6da14Ff3fD6F2b5BD5eC132C9fB93E8A461` |
| Polygon | `0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb` |
| Arbitrum | `0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb` |
| Optimism | `0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb` |
| Base | `0xe20fCBdBfFC4Dd138cE8b2E6FA3F7b91B6f8F7C3` |

## Permit2

Uniswap Permit2 contract (same on all EVM chains):
`0x000000000022D473030F116dDEE9F6B43aC78BA3`

## Known ERC20 Tokens (Ethereum)

| Symbol | Address |
|--------|---------|
| USDC | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| USDT | `0xdAC17F958D2ee523a2206206994597C13D831ec7` |
| DAI | `0x6B175474E89094C44Da98b954EedeAC495271d0F` |
| WETH | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` |
| LINK | `0x514910771AF9Ca656af840dff83E8264EcF986CA` |
| UNI | `0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984` |
| SHIB | `0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE` |

## NFT Collections (Top 8)

| Name | Contract |
|------|----------|
| BoredApeYachtClub | `0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D` |
| CryptoPunks | `0xb47e3cd837dDF8e4c57F05d70Ab865de6e193BBB` |
| MutantApeYachtClub | `0x60E4d786628Fea6478F785A6d7e704777c86a7c6` |
| Azuki | `0xED5AF388653567Af2F388E6224dC7C4b3241C544` |
| CloneX | `0x49cF6f5d44E70224e2E23fDcdd2C053F30aDA28B` |
| Doodles | `0x8a90CAb2b38dba80c64b7734e58Ee1dB38B8992e` |
| PudgyPenguins | `0xBd3531dA5CF5857e7CfAA92426877b022e612cf8` |
| Milady | `0x5Af0D9827E0c53E4799BB226655A1de152A425a5` |

## L2 Native Bridge Contracts

| Chain | RPC | Bridge Contract | Chain ID |
|-------|-----|-----------------|----------|
| Arbitrum | https://arb1.arbitrum.io/rpc | `0x8315177aB297bA92A06054cE80a67Ed4ADd0dF77` | 42161 |
| Base | https://mainnet.base.org | `0x3154Cf16ccdb4C6d922629664174b904d80F2C35` | 8453 |
| Optimism | https://mainnet.optimism.io | `0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1` | 10 |
| Polygon | https://polygon-rpc.com | `0xA0c68C638235ee32657e8f720a23ceC1bFc77C77` | 137 |

## NFT Floor Price API

Reservoir: `https://api.reservoir.tools/collections/v7?id={contract_address}`

## Crypto Price API

CoinGecko: `https://api.coingecko.com/api/v3/simple/price?ids={id}&vs_currencies=usd`
- ETH: `ethereum`
- BTC: `bitcoin`
- SOL: `solana`
- BSC native: `binancecoin`
- DOGE: `dogecoin`
