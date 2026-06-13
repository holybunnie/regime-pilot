# DECISIONS — significant technical choices, in plain English

## Phase 0 (2026-06-13)

1. **RPC endpoints chosen.** Mainnet `bsc-dataseed.bnbchain.org`, testnet `bsc-testnet.publicnode.com`
   — both verified answering live. We keep a backup list (binance, publicnode) for failover in the
   committer daemon.
   *Why:* avoid a single point of failure for the hourly on-chain commits.

2. **Scheduling = long-running loop, not cron.** `crontab` is absent in this Codespace.
   *Why:* the attestation committer will be a resilient long-running process with a heartbeat file
   and auto-restart, which is also more portable to "a cheap always-on box" as the brief requests.

3. **CMC skills source = `openCMC` org.** The org name in the build prompt 404s; `openCMC` is the
   live repo matching the brief. We copy its exact SKILL.md frontmatter format so our skill is
   drop-in installable. (Flagged UNVERIFIED-official in ASSUMPTIONS.md pending brief cross-check.)

4. **SDK decision deferred to Phase 1** per the build spec's decision rule: install
   `bnb-chain/bnbagent-sdk`, test whether it can deploy/call contracts; if yes use it for the
   attestation layer, if no fall back to `web3.py` and document exactly what it lacked. README will
   describe the SDK's real role honestly either way.

5. **Solidity toolchain: TBD.** Neither `solc` nor Foundry is installed. Leaning toward `py-solc-x`
   (pip-installable solc) + `web3.py` to keep the whole stack Python and reproducible with one
   lockfile; will confirm in Phase 7. *Why:* one language, one lockfile, easier determinism story.
