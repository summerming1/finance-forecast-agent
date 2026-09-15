PYTHON ?= python

.PHONY: test demo ui lint

test:
	PYTHONPATH=src $(PYTHON) -m pytest tests -q

demo:
	PYTHONPATH=src $(PYTHON) scripts/run_finance_agent.py

ui:
	PYTHONPATH=src $(PYTHON) -m streamlit run apps/streamlit_app.py

lint:
	PYTHONPATH=src $(PYTHON) -m compileall -q src scripts apps tests
	PYTHONPATH=src $(PYTHON) -m ruff check --select F src scripts apps tests
