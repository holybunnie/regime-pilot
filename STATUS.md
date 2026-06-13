# STATUS — Regime Pilot (plain English, for the operator)

**Last updated:** 2026-06-13 ~13:30 UTC · **Freeze:** 2026-06-21 13:00 UTC (~8 days out).
**Repo:** https://github.com/holybunnie/regime-pilot · **Contract:** [`0xB874…21c1`](https://bscscan.com/address/0xB87481e29b0Dce9545b1B00b8526810679B521c1)

## Bottom line
**All 10 phases are built, tested, and committed.** `make verify` passes top to bottom. The
on-chain attestation runs itself every hour. Two items remain, both external/time-gated: BscScan
source verification (needs a free API key from you) and the reveal on June 20–21.

## Scoreboard
| Phase | State | One-line summary |
|-------|-------|------------------|
| 0 — Environment discovery | ✅ DONE | Machine, APIs, BSC chains, wallet, CMC tier all verified live. `make verify-phase0`. |
| 1 — Data layer | ✅ DONE | 15 tokens × 9,361 hourly bars + CMC Fear&Greed; 0 gaps, live spot-check. `make verify-phase1`. |
| 2 — Spec schema | ✅ DONE | Closed-grammar JSON schema; 8 malformed specs rejected. `make verify-phase2`. |
| 3 — Skill (compiler) | ✅ DONE | Installable CMC-format SKILL.md + compiler prompt + 3 example intents. `make verify-phase3`. |
| 4 — Backtest engine | ✅ DONE | Deterministic + no-lookahead, proven by tests. `make verify-phase4`. |
| 5 — Flagship strategy | ✅ DONE | v1 (−10.4% vs BTC −45%) + v2 (long/short). Embargo enforced. `make verify-phase5`. |
| 6 — Falsification | ✅ DONE | Walk-forward, perturbation, shuffle canary (passed), deflated Sharpe, ablation. `make verify-phase6`. |
| 7 — On-chain attestation | ✅ LIVE | Contract on BSC mainnet; hourly cron (cron-job.org); commits verify. `make verify-phase7`. |
| 8 — x402 data plan | ✅ DONE | Real $0.01 USDC paid on Base (settled); cost plan recomputes. `make verify-phase8`. |
| 9 — Packaging/demo | ✅ DONE | Judge README, offline demo charts, secret-leak gate. `make verify-phase9`. |
| 10 — Verify harness | ✅ DONE | `make verify` = one scoreboard across all phases. |

## The honest headline
In a market that fell **45%**, the long-only v1 lost only **10.4%** (capital preservation); the
live long/short v2 did better out-of-sample (+1.8%, Sharpe ~3.0). But the **deflated Sharpe ≈ 0.01**
for both — meaning **no statistically significant directional edge** over this bear window. We report
that plainly. The differentiator is the *rigor* and the *un-fakeable on-chain forward test*, which is
accruing now and will be the real arbiter.

## Attestation — live and hands-off
- Hourly via **cron-job.org → GitHub `workflow_dispatch` → commit on BSC** (GitHub's own cron was
  unreliable for a new repo, so we drive it externally; verified working).
- Check anytime: `make attest-status` · on-chain: the contract link above · public log:
  `attest/commits_public.csv`.
- Honest record: id=0 is a late manual bootstrap (flagged ⚠️ not-prompt); one early hour is logged
  MISSED (an env-var bug, since fixed). Nothing hidden.

## 🙋 What I need from you (both optional / non-blocking)
1. **BscScan API key** → paste into `.env` as `BSCSCAN_API_KEY`, then I auto-verify the contract
   source so judges can read it. Get it at https://etherscan.io/myapikey (one key works for BSC).
2. **The official 149-token universe list** → drop into `spec/universe.json`; everything re-derives
   (the engine is universe-agnostic). Until then we run a verified interim set of 15 liquid majors.

## How to see it all
```bash
cd regime-pilot
make verify            # full PASS/FAIL scoreboard
make attest-status     # one-line attestation liveness
make demo              # regenerate charts + report bundle offline
cat AGENTS.md          # full audit guide
```
