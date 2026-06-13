# Example intent — graceful refusal (unavailable data)

## Natural-language intent
> "Go short whenever the perpetual **funding rate** flips negative and **open interest** is in the
> top decile, and use **order-book depth** to size. Long when funding is deeply positive."

## Why the compiler must NOT just comply
The strategy is entirely built on **funding rate, open interest, and order-book depth**. On the
current CoinMarketCap data tier:
- `funding_rate` — **not available**
- `open_interest` — **not available**
- order-book depth — **not available at all** (no such data source)

Fabricating these, or silently dropping them and shipping a different strategy, would be dishonest
and would make the engine raise at runtime (it refuses unfetched sources — no synthetic fill). So
the skill **does not emit a spec**.

## Correct response (what the skill says back)
> "I can't compile this as written — funding rate, open interest, and order-book depth aren't
> available on your current data tier, and they're the core of your idea. Two options:
> 1. **Upgrade / pay-per-call (x402)** to unlock funding & OI, and I'll build it as specified; or
> 2. **Closest legal approximation now:** proxy 'leverage fragility' with `fear_greed` extremes +
>    `btc_vol` percentile (high fear/greed + stretched vol ≈ crowded positioning), and trade the
>    regime instead of raw funding. It won't be identical, and I'll label it as a proxy.
> Which do you want? I won't ship a spec that pretends to use data we don't have."

## Outcome
No spec file is produced unless the user accepts option 1 (after enabling the data) or option 2
(the documented proxy). This demonstrates the skill's honesty guardrail: **degrade transparently
or refuse — never fake data.**
