.PHONY: test gate smoke watch clean
SCENARIO ?= source_fidelity
RUN      ?= smoke
N        ?= 60

# Everything a change must pass before it is believed. `smoke` ends by printing
# complete raw records because reading them is a step, not a courtesy: on this
# instrument it has caught defects that every aggregate table showed as normal.

test:
	uv run pytest

gate:
	uv run python -m analysis.gate $(SCENARIO) --n $(N)

smoke: test
	uv run python -m analysis.gate $(SCENARIO) --n 30 || true
	uv run python -m tabib.campaign $(SCENARIO) $(RUN) --models dev --n 2
	@echo "\n=== read these before believing any number ==="
	uv run python -m analysis.raw runs/$(RUN)/$(SCENARIO) --per 1

# during a campaign, from any machine that can see the log directory
watch:
	uv run inspect view --log-dir runs/$(RUN)/$(SCENARIO)

clean:
	rm -rf logs/_gate .pytest_cache
