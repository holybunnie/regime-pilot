# Reveal Dry-Run — full commit → reveal → verify on an in-memory EVM (eth-tester)

Proves the reveal-day **procedure** end-to-end with zero funds. The compiled contract is the
**byte-identical** `SignalAttestor` deployed and source-verified on BSC mainnet; only the chain
underneath differs (in-memory py-evm instead of BSC). This is sufficient because reveal day
carries no *contract* risk — the live contract already holds 50+ source-verified commits — only
*reveal-script* risk: that the saved payloads + deterministic salts recompute to the on-chain
hashes. That recomputation is exactly what this rehearsal exercises against the real bytecode.

- Chain: in-memory EVM (eth-tester / py-evm) — **not** a public testnet; no network, no funds
- Sample signals committed & revealed: **5**
- Revealed payloads that recompute to their on-chain hash: **5/5**
- Promptness (commit within [T, T+1h)) is N/A on an in-memory EVM (synthetic clock);
  it is verified against the real mainnet record by `make attest-verify`.
- A public BSC-testnet run would add clickable tx links but no extra proof of correctness;
  the script is identical — supply a funded testnet key to produce them.

| id | decision hour | regime | reveal reproduces hash |
|--:|---------------|--------|:----------------------:|
| 0 | 2026-06-13T13:00:00Z | downtrend | ✅ |
| 1 | 2026-06-13T14:00:00Z | chop | ✅ |
| 2 | 2026-06-13T15:00:00Z | trend_up | ✅ |
| 3 | 2026-06-13T16:00:00Z | chop | ✅ |
| 4 | 2026-06-13T17:00:00Z | downtrend | ✅ |

**ALL REVEALS REPRODUCE — reveal day is a replay.**
