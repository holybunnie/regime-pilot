# STATUS — Regime Pilot (plain English, for the operator)

**Last updated:** 2026-06-19 · **Freeze:** 2026-06-21 13:00 UTC.
**Repo:** https://github.com/holybunnie/regime-pilot · **Contract:** [`0xB874…21c1`](https://bscscan.com/address/0xB87481e29b0Dce9545b1B00b8526810679B521c1)

## Bottom line
**All components are built, tested, committed, and live on `main`.** `make verify` (offline) passes
top to bottom on a fresh clone with no secrets and no downloaded data; `make verify-full` is
**previously confirmed passing live** (CMC Basic key + `make data`) — data integrity, skill, strategy, and the
full chain-complete attestation all green. The on-chain attestation runs itself every hour (now with
the duplicate-commit guard live), and the **contract source is verified on BscScan** (exact bytecode
+ ABI match). The only remaining live event is the **reveal on June 20–21** — scripted, and already
rehearsed end-to-end against a real EVM (`attest/REVEAL_DRYRUN.md`).

**New but deliberately inactive:** the operator reports CMC **Pro** access is provisioned. The real
hourly CMC OHLCV adapter and shadow cache path are built, but the frozen v2 committer remains on its
original source through reveal. Run `make verify-cmc-pro` in the secret-bearing environment, then
perform a documented v3 cutover after reveal. The official **149-token** universe remains pending.

**CMC Pro verified 2026-06-19:** hourly historical access passes; a separate 364-day, 15-asset
shadow cache was built successfully and the current v2 strategy completed a CMC-backed shadow
backtest. This does not activate CMC for the cron.

## Scoreboard
| Component | State | One-line summary |
|-------|-------|------------------|
| Environment / credentials | ✅ DONE | Machine, APIs, BSC chains, wallet, CMC tier verified live. `make verify-environment` (live). |
| Data layer | ✅ DONE | 15 tokens hourly OHLCV + CMC Fear&Greed; 0 gaps, source spot-check. `make verify-data` (live). |
| Spec schema | ✅ DONE | Closed-grammar JSON schema; malformed specs rejected. `make verify-spec`. |
| Skill (compiler) | ✅ DONE | Valid skill package + compiler prompt + examples. `make verify-skill`. |
| Backtest engine | ✅ DONE | Deterministic + no-lookahead, proven on a committed fixture. `make verify-engine`. |
| Flagship strategy | ✅ DONE | v1 (−10.4%) + v2 (−10.9%) vs BTC −44.7%. Embargo enforced. `make verify-strategy` (live). |
| Falsification | ✅ DONE | Walk-forward, perturbation, shuffle canary (passed), deflated Sharpe, ablation. `make verify-falsification`. |
| On-chain attestation | ✅ LIVE | Contract on BSC mainnet; hourly committer; every commit accounted for. `make attest-verify`. |
| Duplicate-commit guard | ✅ DONE | Single-flight + on-chain pre-send guard close the id-7/26 race. `make verify-attest-race`. |
| x402 data plan | ✅ DONE | Real $0.01 USDC paid on Base (settled); cost plan recomputes. `make verify-x402`. |
| Secret-leak gate | ✅ DONE | No secrets in files or full git history. `make verify-secrets`. |
| Verify harness | ✅ DONE | `make verify` = one offline scoreboard; `make verify-full` = live checks. |

## The honest headline (read in order)
**1. Full-window result first.** In a market that fell **44.7%**, the long-only **v1 returned −10.4%**
and the live long/short **v2 returned −10.9%** — v2 is *slightly worse* on the headline number. v1's
−10.4% is **capital preservation, not alpha** (it routed to cash through the decline).
**2. Walk-forward selection was all negative** for both versions (grid Sharpes ≈ −1.9 to −3.2).
**3. The one favourable slice** (+1.8%, Sharpe ~3.0) is a **single out-of-sample window** of ~30 days,
**not representative** — we do not headline it.
**4. Deflated Sharpe ≈ 0.01** (v1 0.012, v2 0.013) ⇒ **no statistically significant** directional edge
over this window, for either version. The differentiator is the *rigor* and the *un-fakeable on-chain
forward test*, which is accruing now and will be the real arbiter.

## Attestation — live and hands-off
- Hourly via GitHub Actions (`.github/workflows/attest.yml`) → `attest/commit_hour.py` → commit on BSC.
- Check anytime: `make attest-status` · on-chain: the contract link above · public log:
  `attest/commits_public.csv` · full per-id ledger: `attest/onchain_ledger.json`.
- **Honest record:** the chain grows by one commit per hour (live count tracked in
  `attest/onchain_ledger.json`); two ids (**7** and **26**) are exact duplicates of the commits
  before them — a second hourly run for the same hour produced the same deterministic hash. They
  sign nothing new and are fully documented in `attest/RECONCILIATION.md`.
  The duplicate-commit race that caused them is now closed (`make verify-attest-race`). One early
  hour is logged MISSED (an env-var bug, since fixed). Nothing hidden — `make attest-verify` accounts
  for every on-chain id, online and offline, and is robust to the cron adding a new commit
  mid-check (a newer id is flagged "pending sync," never a false gap).

## 🙋 What I need from you (optional / non-blocking)
1. **The official 149-token universe list** → replace `spec/universe_official_149.json` and flip the
   one config line (`make verify-universe` validates the swap). Until then we run a verified interim
   set of 15 liquid majors; the engine is universe-agnostic.
2. After reveal, choose the exact v3 cutover hour. CMC Pro access and the shadow cache are verified;
   activation remains intentionally separate from the frozen v2 forward record.

## How to see it all
```bash
cd regime-pilot
make verify            # OFFLINE PASS/FAIL scoreboard (no secrets, no network)
make verify-full       # live checks (needs CMC key + make data)
make attest-status     # one-line attestation liveness
make demo              # regenerate charts + report bundle offline
```
