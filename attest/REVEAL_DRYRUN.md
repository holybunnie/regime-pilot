# Reveal Dry-Run — full commit → reveal → verify on a real EVM (eth-tester)

Proves the reveal-day procedure end-to-end with zero funds. The compiled contract is
the same `SignalAttestor` that is deployed on BSC mainnet; only the chain differs.

- Chain: in-memory EVM (eth-tester / py-evm) — no network, no funds
- Sample signals committed & revealed: **5**
- Revealed payloads that recompute to their on-chain hash: **5/5**
- Promptness (commit within [T, T+1h)) is N/A on an in-memory EVM (synthetic clock);
  it is verified against the real mainnet record by `make attest-verify`.
- For public BSC-testnet tx links, supply a funded testnet key — the script is identical.

| id | decision hour | regime | reveal reproduces hash |
|--:|---------------|--------|:----------------------:|
| 0 | 2026-06-13T13:00:00Z | downtrend | ✅ |
| 1 | 2026-06-13T14:00:00Z | chop | ✅ |
| 2 | 2026-06-13T15:00:00Z | trend_up | ✅ |
| 3 | 2026-06-13T16:00:00Z | chop | ✅ |
| 4 | 2026-06-13T17:00:00Z | downtrend | ✅ |

**ALL REVEALS REPRODUCE — reveal day is a replay.**
