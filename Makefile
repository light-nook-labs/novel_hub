.PHONY: run clean

run:
	uv run main.py

dev:
	uv run dev.py

clean:
	rm -rf __pycache__ *.pyc