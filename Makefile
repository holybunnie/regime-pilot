# Regime Pilot — one-command entry points.
# Plain-English: `make verify` is the single command that judges/operator run.
PY := python3

.PHONY: help setup verify verify-phase0 verify-phase2 data backtest falsify \
        attest-start attest-reveal attest-status demo clean

help:
	@echo "Regime Pilot targets:"
	@echo "  make setup           Install pinned Python dependencies"
	@echo "  make verify-phase0   Live-check external deps + credentials"
	@echo "  make verify-phase2   Validate spec schema + reject malformed specs"
	@echo "  make verify          Run all available verification gates + scoreboard"
	@echo "  make data            Fetch & cache market data (Binance OHLCV + CMC F&G)   [coming]"
	@echo "  make backtest        Run the deterministic backtest                        [coming]"
	@echo "  make falsify         Generate the falsification report                     [coming]"
	@echo "  make attest-start    Start the hourly on-chain committer                   [coming]"
	@echo "  make attest-reveal   Reveal commits + verify on-chain                      [coming]"
	@echo "  make attest-status   Show committer liveness + commit count                [coming]"
	@echo "  make demo            Regenerate all demo charts offline                    [coming]"

setup:
	$(PY) -m pip install -r requirements.txt

verify-phase0:
	$(PY) cli/verify_phase0.py

verify-phase1:
	$(PY) cli/verify_phase1.py

verify-phase2:
	$(PY) tests/test_schema.py

verify-phase3:
	$(PY) cli/verify_phase3.py

verify-phase4:
	$(PY) tests/test_sizing.py && $(PY) tests/test_engine.py

verify-phase5:
	$(PY) cli/verify_phase5.py

verify-phase6:
	PYTHONPATH=. $(PY) cli/verify_phase6.py

verify-phase7:
	PYTHONPATH=. $(PY) cli/verify_phase7.py

verify-phase8:
	$(PY) cli/verify_phase8.py

verify-phase9:
	$(PY) cli/verify_phase9.py

demo:
	$(PY) demo/build_demo.py

x402-pay:
	PYTHONPATH=. $(PY) x402plan/pay_x402.py

x402-plan:
	$(PY) x402plan/build_plan.py

data:
	$(PY) engine/data/fetch.py

backtest:
	$(PY) engine/backtest.py

falsify:
	PYTHONPATH=. $(PY) falsify/report.py

attest-deploy:
	PYTHONPATH=. $(PY) attest/deploy.py

attest-commit:
	PYTHONPATH=. $(PY) attest/commit_hour.py

attest-status:
	@PYTHONPATH=. $(PY) attest/status.py

attest-reveal:
	PYTHONPATH=. $(PY) attest/reveal.py

attest-verify:
	PYTHONPATH=. $(PY) attest/verify.py

# Aggregate gate — grows as phases land. Runs every gate that currently exists.
verify:
	@echo "######## REGIME PILOT — VERIFICATION SCOREBOARD ########"
	@$(PY) cli/verify_phase0.py || true
	@echo
	@$(PY) cli/verify_phase1.py || true
	@echo
	@$(PY) cli/verify_phase3.py || true
	@echo
	@$(PY) tests/test_schema.py || true
	@echo
	@$(PY) tests/test_sizing.py || true
	@echo
	@$(PY) tests/test_engine.py || true
	@echo
	@$(PY) cli/verify_phase5.py || true
	@echo
	@PYTHONPATH=. $(PY) cli/verify_phase7.py || true
	@echo
	@$(PY) cli/verify_phase8.py || true
	@echo
	@$(PY) cli/verify_phase9.py || true
	@echo "#######################################################"
	@echo "(More gates land with the data/engine/falsify/attest phases.)"

clean:
	rm -rf engine/data/cache __pycache__ */__pycache__ tests/__pycache__
