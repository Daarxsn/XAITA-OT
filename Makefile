test:
	PYTHONPATH=src pytest -q
smoke:
	PYTHONPATH=src python scripts/smoke_test.py
api:
	PYTHONPATH=src python run_api.py
