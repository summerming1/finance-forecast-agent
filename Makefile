PYTHON ?= python

.PHONY: test test-unit test-integration demo ui lint

test: test-unit test-integration

test-unit:
	PYTHONPATH=src $(PYTHON) -m pytest tests -q

test-integration:
	PYTHONPATH=src $(PYTHON) -m pytest tests/test_harness.py -q

demo:
	PYTHONPATH=src $(PYTHON) scripts/run_finance_agent.py

ui:
	PYTHONPATH=src $(PYTHON) -m streamlit run apps/streamlit_app.py

lint:
	PYTHONPATH=src $(PYTHON) -m compileall -q src scripts apps tests
