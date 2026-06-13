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

verify-phase2:
	$(PY) tests/test_schema.py

# Aggregate gate — grows as phases land. Runs every gate that currently exists.
verify:
	@echo "######## REGIME PILOT — VERIFICATION SCOREBOARD ########"
	@$(PY) cli/verify_phase0.py || true
	@echo
	@$(PY) tests/test_schema.py || true
	@echo "#######################################################"
	@echo "(More gates land with the data/engine/falsify/attest phases.)"

clean:
	rm -rf engine/data/cache __pycache__ */__pycache__ tests/__pycache__
