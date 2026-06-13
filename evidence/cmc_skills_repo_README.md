# Official CoinMarketCap Skills for AI Agents

A collection of skills that enable AI agents to access CoinMarketCap data for cryptocurrency market information, prices, technical analysis, news, and trends.

## Skills

### MCP Skills (Real-time Data via MCP)

| Skill | Description |
|-------|-------------|
| [cmc-mcp](skills/cmc-mcp/SKILL.md) | Fetches cryptocurrency market data using the CoinMarketCap MCP. Provides prices, technical analysis, news, holder metrics, trending narratives, and global market data. |
| [market-report](skills/market-report/SKILL.md) | Generates comprehensive daily/weekly market reports combining global metrics, fear/greed, trending narratives, derivatives data, and upcoming catalysts. |
| [crypto-research](skills/crypto-research/SKILL.md) | Performs due diligence on any token with structured analysis of fundamentals, tokenomics, holder distribution, technicals, and risk factors. |

### x402 Skills (Pay-per-Request via USDC)

| Skill | Description |
|-------|-------------|
| [cmc-x402](skills/cmc-x402/SKILL.md) | Access CMC data via x402 pay-per-request protocol. Pay $0.01 USDC per request on Base. No API key required. |

### API Skills (Direct API Integration)

| Skill | Description | APIs |
|-------|-------------|------|
| [cmc-api-crypto](skills/cmc-api-crypto/SKILL.md) | Cryptocurrency data APIs for listings, quotes, OHLCV, categories, trending, and market pairs. | 16 endpoints |
| [cmc-api-dex](skills/cmc-api-dex/SKILL.md) | DEX (decentralized exchange) APIs for on-chain token data, prices, pools, transactions, and security analysis. | 18 endpoints |
| [cmc-api-exchange](skills/cmc-api-exchange/SKILL.md) | Centralized exchange APIs for exchange info, listings, volume, market pairs, and assets. | 7 endpoints |
| [cmc-api-market](skills/cmc-api-market/SKILL.md) | Market-wide APIs for global metrics, fear/greed index, CMC indices, community trends, content, charts, and utilities. | 19 endpoints |

## Installation

### For MCP Skills

1. Copy the skill folder to your agent's skills directory:

```bash
cp -r skills/cmc-mcp /path/to/your/skills/directory/
```

2. Set up the CoinMarketCap MCP in your MCP configuration:

```json
{
  "mcpServers": {
    "cmc-mcp": {
      "url": "https://mcp.coinmarketcap.com/mcp",
      "headers": {
        "X-CMC-MCP-API-KEY": "your-api-key"
      }
    }
  }
}
```

3. Get your API key from https://pro.coinmarketcap.com/login

### For x402 Skills

1. Copy the skill folder to your agent's skills directory:

```bash
cp -r skills/cmc-x402 /path/to/your/skills/directory/
```

2. Install the x402 TypeScript SDK:

```bash
npm install @x402/axios @x402/evm viem
```

3. Fund a wallet with USDC on Base (Chain ID: 8453)

4. Set your wallet private key as an environment variable (keep secure)

See [cmc-x402/SKILL.md](skills/cmc-x402/SKILL.md) for complete integration examples.

### For API Skills

1. Copy the skill folder to your agent's skills directory:

```bash
cp -r skills/cmc-api-crypto /path/to/your/skills/directory/
```

2. Get your API key from https://pro.coinmarketcap.com/login

3. The skills will guide your agent to call APIs using:
   - Base URL: `https://pro-api.coinmarketcap.com`
   - Auth header: `X-CMC_PRO_API_KEY: your-api-key`

## Validation

### Test MCP Skills

**Simple (cmc-mcp):**
- "What is the current price of Bitcoin?"
- "How is ETH doing?"

**Market Report (market-report):**
- "Give me a market report"
- "What's happening in crypto today?"

**Token Research (crypto-research):**
- "Research Solana for me"
- "Due diligence on LINK"

### Test API Skills

**Crypto API (cmc-api-crypto):**
- "How do I get the top 100 cryptocurrencies using the CMC API?"
- "Call the CMC API to get Bitcoin's price"

**DEX API (cmc-api-dex):**
- "How do I look up a token on Uniswap using CMC API?"
- "Get DEX token security info"

**Exchange API (cmc-api-exchange):**
- "List all exchanges using CMC API"
- "Get Binance trading pairs"

**Market API (cmc-api-market):**
- "How do I get the fear and greed index via API?"
- "Call CMC API for global market metrics"

### Test x402 Skills

**x402 (cmc-x402):**
- "How do I use x402 to get Bitcoin's price?"
- "Set up pay-per-request for CMC data"
- "Make an x402 request to CMC"

## License

MIT
