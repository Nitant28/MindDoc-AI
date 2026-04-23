# Makefile — developer shortcuts (works on macOS/Linux; use setup.bat on Windows)
.PHONY: setup start stop reset logs
setup:
	python setup.py
start:
	python setup.py --start-only
stop:
	docker compose down
reset:
	docker compose down -v
	python setup.py
logs:
	docker compose logs -f backend
shell-db:
	docker compose exec postgres psql -U minddoc -d minddoc_ai
