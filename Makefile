# Regime Pilot — one-command entry points.
# Plain-English: `make verify` (offline) is the single command judges/operator run.
PY := python3

.PHONY: help setup verify verify-full \
        verify-spec verify-engine verify-falsification verify-secrets verify-x402 \
        verify-environment verify-data verify-skill verify-strategy verify-attestation \
        verify-framing verify-readme verify-universe verify-datasource \
        verify-docs-consistency verify-datasources verify-attest-race \
        data backtest falsify demo clean \
        attest-deploy attest-commit attest-status attest-reveal attest-verify x402-pay x402-plan

help:
	@echo "Regime Pilot targets:"
	@echo "  make setup            Install pinned Python dependencies"
	@echo "  make verify           OFFLINE scoreboard — no secrets, no network (the headline)"
	@echo "  make verify-full      Live checks (needs CMC key + make data)"
	@echo "  -- claim-based gates (offline) --"
	@echo "  make verify-spec            Bad specs rejected, good ones accepted"
	@echo "  make verify-engine          Backtest deterministic + no-lookahead + sizing (fixture)"
	@echo "  make verify-falsification   Falsification battery + deflated-Sharpe known-answer"
	@echo "  make verify-x402            x402 payment real + plan recomputes"
	@echo "  make verify-secrets         No secrets in files or git history"
	@echo "  make verify-attest-race     Duplicate-commit race is closed"
	@echo "  make attest-verify          Every on-chain commit accounted for (offline snapshot)"
	@echo "  -- claim-based gates (live; part of verify-full) --"
	@echo "  make verify-environment     External deps + credentials reachable"
	@echo "  make verify-data            Cached data has no gaps/dupes; matches source"
	@echo "  make verify-skill           Skill installable + LLM quarantined"
	@echo "  make verify-strategy        Flagship backtest runs; embargo enforced"
	@echo "  make verify-attestation     Live contract + commits verify on-chain"

setup:
	$(PY) -m pip install -r requirements.txt

# ---- claim-based verification gates (offline) ----
verify-spec:
	$(PY) tests/test_schema.py

verify-engine:
	PYTHONPATH=. $(PY) cli/verify_engine.py

verify-falsification:
	PYTHONPATH=. $(PY) cli/verify_phase6.py

verify-x402:
	$(PY) cli/verify_phase8.py

verify-secrets:
	$(PY) cli/verify_phase9.py

verify-framing:
	$(PY) cli/verify_framing.py

verify-readme:
	$(PY) cli/verify_readme.py

verify-universe:
	PYTHONPATH=. $(PY) cli/verify_universe.py

verify-datasource:
	PYTHONPATH=. $(PY) cli/verify_datasource.py

verify-docs-consistency:
	$(PY) cli/verify_docs_consistency.py

verify-datasources:
	$(PY) cli/verify_datasources.py

verify-attest-race:
	PYTHONPATH=. $(PY) cli/verify_attest_race.py

attest-verify:
	PYTHONPATH=. $(PY) attest/verify.py

# ---- claim-based verification gates (live; require credentials/data) ----
verify-environment:
	$(PY) cli/verify_phase0.py

verify-data:
	$(PY) cli/verify_phase1.py

verify-skill:
	$(PY) cli/verify_phase3.py

verify-strategy:
	$(PY) cli/verify_phase5.py

verify-attestation:
	PYTHONPATH=. $(PY) cli/verify_phase7.py

# ---- the headline: one offline scoreboard ----
verify:
	@PYTHONPATH=. $(PY) cli/verify.py

# ---- live aggregate (needs CMC key + downloaded data) ----
verify-full: verify
	@echo
	@echo "######## LIVE CHECKS (need CMC key + make data) ########"
	@$(PY) cli/verify_phase0.py || true
	@echo
	@$(PY) cli/verify_phase1.py || true
	@echo
	@$(PY) cli/verify_phase3.py || true
	@echo
	@$(PY) cli/verify_phase5.py || true
	@echo
	@PYTHONPATH=. $(PY) cli/verify_phase7.py || true
	@echo "#######################################################"

# ---- build / run ----
data:
	$(PY) engine/data/fetch.py

backtest:
	$(PY) engine/backtest.py

falsify:
	PYTHONPATH=. $(PY) falsify/report.py

demo:
	$(PY) demo/build_demo.py

x402-pay:
	PYTHONPATH=. $(PY) x402plan/pay_x402.py

x402-plan:
	$(PY) x402plan/build_plan.py

attest-deploy:
	PYTHONPATH=. $(PY) attest/deploy.py

attest-commit:
	PYTHONPATH=. $(PY) attest/commit_hour.py

attest-status:
	@PYTHONPATH=. $(PY) attest/status.py

attest-reveal:
	PYTHONPATH=. $(PY) attest/reveal.py

clean:
	rm -rf engine/data/cache __pycache__ */__pycache__ tests/__pycache__
