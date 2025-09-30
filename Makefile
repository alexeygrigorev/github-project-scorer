.PHONY: run test

run:
	uv run python main.py

test:
	uv run pytest tests