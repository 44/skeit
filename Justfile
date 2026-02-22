lint:
	uvx ruff check .

format:
	uvx ruff format .

check: lint format
