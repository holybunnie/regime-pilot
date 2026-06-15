# SELF_AUDIT — ten hostile questions, answered

This document plays adversary against our own submission. Each item is the sharpest version of
a question a skeptical judge would ask, answered honestly, followed by the **residual risk** we
have *not* fully eliminated. Nothing here is spin: where the honest answer is "this is a real
limitation," we say so. Every factual claim below is checkable with a command listed in the
README's reproduce table or with `make verify`.

The frame to keep in mind: **the contribution is the trustworthy measurement system; the
strategy is the test subject.** Several "weaknesses" below (a weak strategy result, a bear-market
window) are not failures of the project — they are the measurement system working as designed and
reporting an unflattering truth instead of hiding it.

---

## Q1. "Two on-chain commits (7 and 26) aren't in your public CSV. What are you hiding?"

**Answer.** Nothing — and we surface them rather than bury them. Ids 7 and 26 are **exact
duplicates** of ids 6 and 25: byte-identical on-chain hashes, posted ~3 minutes later by a second
GitHub Actions run that fired for the *same decision hour*. Because the committed value is
`keccak256(canonical_json(signal) || salt)` and the salt is derived only from the secret seed and
the decision-hour timestamp, an identical hash is *only* possible if both runs committed the same
prediction for the same hour. A tampered or different prediction would have produced a different
hash. They are absent from `commits_public.csv` only because that file records one row per
decision hour. Full write-up: `attest/RECONCILIATION.md`; both are listed in
`attest/commits_reconciliation.csv` and flagged `DOCUMENTED-DUPLICATE ⚠️` in `VERIFICATION.md`.

**Residual risk.** The duplicates existed because idempotency was originally checked against the
post-send CSV, not a pre-send lock. We have closed the race (Item 2: single-flight lock +
pre-send on-chain duplicate guard + `cancel-in-progress: true`), but that fix landed *after* the
two duplicates were already on-chain. They are permanent, harmless artifacts on the public ledger.

## Q2. "Your verifier loops your CSV, so of course everything matches. Circular."

**Answer.** It does not. `attest/verify.py` iterates the **contract's own `commitCount()`** (34
ids, 0–33) and must account for *every* on-chain id, not just the ones we chose to list. Each id
is classified REPRODUCED / DOCUMENTED-DUPLICATE / RECORDED with a reason; the pass condition is
**zero unaccounted ids**. If a commit existed on-chain that we had never disclosed, the verifier
would fail. This is the opposite of circular: the chain is the source of truth and the CSV is
checked against it.

**Residual risk.** Until reveal day (June 20–21) the *payloads* are not yet public, so an outside
auditor can confirm the ledger is complete and internally consistent but cannot independently
recompute each hash from a revealed payload. That capability switches on at reveal; we rehearsed
the whole reveal→verify path on an in-memory EVM (`make attest-dryrun-verify`, 5/5 reproduce).

## Q3. "You lead with +1.8% / Sharpe ~3.0. That's cherry-picking."

**Answer.** We deliberately do *not* lead with it. The README, STATUS, and falsification summaries
present results in this order: (1) full-window — **v1 −10.4%, v2 −10.9%**; (2) the walk-forward
folds, all negative; (3) only then the embargo slice, **explicitly labelled "a single
out-of-sample window of ~30 days, not representative"**; (4) the deflated Sharpe. The +1.8% is
shown as the weakest form of evidence, not the headline. `make verify-framing` mechanically
asserts that no headline figure appears before the full-window figure and that the phrases "no
statistically significant" and "single out-of-sample window" are present.

**Residual risk.** A reader skimming only the embargo number in isolation could still over-read
it. We mitigate with labels and ordering, but we cannot control selective quotation.

## Q4. "So your strategy makes no money. Why should this win anything?"

**Answer.** Correct, and that is the point. The deflated Sharpe is **0.012 (v1) / 0.013 (v2)** —
**no statistically significant directional edge** over the tested window. We say this plainly
everywhere. The submission is not "we found alpha"; it is "we built a system that can tell you,
*honestly and unfakeably*, whether an AI-authored strategy has an edge — and when pointed at our
own strategy it correctly reports *no*." An overfit project would have buried this; ours headlines
it. v1's −10.4% in a −44.7% market is framed as **capital preservation, not alpha** (it routed to
cash in downtrends), which is an honest description of defensive behaviour, not a performance
claim.

**Residual risk.** Judges who score purely on strategy P&L rather than on the verification
contribution will not be moved by this. That is a positioning risk we accept knowingly.

## Q5. "'Committed before the outcome is known' — but the hour has already started when you commit."

**Answer.** We reworded this to be precise (Item 7). Commits land within the **first minutes of
hour T** (observed :02–:46), and the measured return is the T→T+1h move — so a few minutes of that
hour's price action is already realized at commit time. The honest statement we now use:
*"committed within the first minutes of hour T, before essentially all of the T→T+1h outcome is
realized; the signal itself is computed only from data strictly before T (≤ T−1h)."* The signal's
**inputs** contain zero lookahead; the timing claim is about how little of the *outcome* is
realized at stamp time, stated exactly.

**Residual risk.** "Essentially all" is not "all." A few minutes of the first hour's move is
realized pre-commit. We do not claim otherwise, and the on-chain block timestamp makes the exact
commit moment independently auditable, so anyone can quantify the gap themselves.

## Q6. "Your prices come from Binance, but this is a CoinMarketCap-sponsored track."

**Answer.** The backtest uses Binance public hourly OHLCV because the operator's CMC tier does not
expose price *history*; sentiment (Fear & Greed) and the **live attested signal** are CMC. This is
disclosed in the limitations, not foregrounded as a verification claim (we explicitly removed the
old "matches live Binance" headline — Item 10). A CMC-Pro data-source abstraction is wired and
optional (`engine/datasource.py`, `DATA_PLAN.md`): with a Pro key the system sources first-party
CMC prices/history/derivatives without any engine change. We also executed **one real $0.01 USDC
x402 payment** to prove first-party CMC derivatives are reachable.

**Residual risk.** Pro API access was not provided during the build, so the headline backtest runs
on hybrid data today. Wiring Pro is a config change that improves data *coherence*, not something
expected to manufacture an edge — and we will treat any CMC-data rerun as clearly-labelled
*supplementary*, never a replacement of the attested forward record.

## Q7. "15 tokens, not the official 149. You didn't finish the brief."

**Answer.** The engine is universe-agnostic; switching is a **one-line config change**. We ship
`spec/universe_official_149.json` (the full BEP-20 list, schema-validated, unresolved tickers
flagged not crashed) and a gate, `make verify-universe`, that loads both files and confirms the
engine runs against the active set. The interim 15-major universe is in place only because the
team's official symbol-resolution list was not available on the free tier in time.

**Residual risk.** We have not *run the full backtest* on all 149 tokens (data for the long tail
isn't fetched), so we cannot show 149-token results today. The claim is "engine ready + swap
verified," not "149-token results produced."

## Q8. "Anyone can deploy a contract. How do we know the live record is real and yours?"

**Answer.** The contract (`0xB87481e29b0Dce9545b1B00b8526810679B521c1`, BSC mainnet) has
**verified source on BscScan** (exact match), so the commit/reveal logic is auditable. Commits
arrive hourly with on-chain block timestamps you can read directly; the cadence and the
deterministic-salt recipe are documented. At reveal, every payload recomputes to its already-
on-chain hash — a hash that was fixed *before* the outcome window — which is the property that
makes the forward test impossible to curve-fit after the fact.

**Residual risk.** Until reveal, verification is **owner-only** (we hold the salt seed; outsiders
see hashes, not payloads). This is inherent to commit-reveal — early disclosure would defeat the
scheme. The trust gap closes entirely on reveal day, which we have rehearsed end-to-end.

## Q9. "An LLM wrote this. How do we know it didn't 'help' the results?"

**Answer.** The LLM appears in exactly one place — **authoring the JSON spec** — and never touches
execution, data, or results. The spec is a strict closed-grammar AST (no code), validated by
`spec/schema.json`; malformed/unsafe specs are rejected (`make verify-spec`). Downstream, the
backtest is deterministic and lookahead-guarded (`make verify-engine`: byte-identical reruns, a
`GuardedAccessor` that rejects future reads, a 1-hour feature shift). The strategy's numbers come
from code the LLM cannot influence at runtime.

**Residual risk.** The LLM *chose* the strategy's structure (regime routing, percentile
thresholds), so human/LLM design judgment is in the loop at authoring time. We account for that
exposure with the deflated Sharpe (penalizing the 27 configurations tried) and the shuffle canary,
which is exactly how you keep author-side discretion from inflating the result.

## Q10. "Reveal day has never actually happened. What if it breaks on June 20?"

**Answer.** It will not be the first execution. We rehearsed the **complete** commit→reveal→verify
flow on a real in-memory EVM (eth-tester/py-evm) using the same compiled `SignalAttestor` and the
real salt+canonical-JSON recipe: 5 signals committed, revealed, and **5/5 recompute to their
on-chain hash** (`make attest-dryrun-verify`, `attest/REVEAL_DRYRUN.md`). The reveal-day runbook
(commands, order, expected output) is documented in the README. Reveal day is a replay of a proven
procedure.

**Residual risk.** The rehearsal ran on an in-memory chain, not public BSC testnet, so it does not
produce public testnet tx links (a funded testnet key would; the script is byte-identical either
way). And promptness — block ts within [T, T+1h) — is N/A on a synthetic-clock EVM; that check
runs against the real mainnet record in `attest/verify.py`. The mainnet reveal transaction itself
is the one step that, by construction, can only happen live on June 20–21.

---

### Honest bottom line

The strongest true criticism of this submission is **Q4 + Q8 combined**: the strategy has no
proven edge, and full independent verification of the live record only unlocks at reveal. We do not
dispute either. We argue the project should be judged on what it actually contributes — a
deterministic, falsification-tested, on-chain-notarized measurement system that reports an honest
"no edge" instead of a flattering lie — and on the fact that every other claim here is backed by a
command a judge can run in under a minute.
