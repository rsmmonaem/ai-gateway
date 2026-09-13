.PHONY: help setup dev run test benchmark docker-up docker-down run-open-webui cli backup restore

help:
	@echo "AI Model Gateway Commands (Apple Silicon M5 16 GB):"
	@echo "  make setup            Run full macOS Apple Silicon setup script"
	@echo "  make run              Start the Gateway locally with uvicorn (Port 8000)"
	@echo "  make test             Execute automated pytest test suite"
	@echo "  make benchmark        Run latency & TTFT benchmark script"
	@echo "  make run-open-webui   Launch Open WebUI (ChatGPT-like interface) on Port 3000"
	@echo "  make docker-up        Start PostgreSQL, Redis, and Gateway via Docker"
	@echo "  make docker-down      Stop Docker containers"
	@echo "  make run-llamacpp     Launch llama-server for Qwen 27B GGUF"
	@echo "  make run-ollama       Launch Ollama server (0.34.0)"
	@echo "  make cli              Run Gateway administration CLI"

setup:
	./infrastructure/scripts/setup-mac-m4.sh

run:
	cd backend && ( [ -f .venv/bin/uvicorn ] && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload || python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload )

test:
	cd backend && ( [ -f .venv/bin/pytest ] && .venv/bin/pytest -v tests/ || pytest -v tests/ )

benchmark:
	cd backend && ( [ -f .venv/bin/python ] && .venv/bin/python scripts/benchmark.py || python3 scripts/benchmark.py )

run-open-webui:
	docker compose -f infrastructure/docker-compose.open-webui.yml up -d

docker-up:
	cd infrastructure && docker compose up -d --build

docker-down:
	cd infrastructure && docker compose down && docker compose -f docker-compose.open-webui.yml down

run-llamacpp:
	llama-server --host 127.0.0.1 --port 8082 -m ./models/qwen2.5-27b-instruct-q3_k_m.gguf -c 4096 --ngl 99

run-ollama:
	./infrastructure/scripts/run-ollama.sh

cli:
	./backend/bin/ai-gateway $(filter-out $@,$(MAKECMDGOALS))

backup:
	./infrastructure/scripts/backup.sh

restore:
	./infrastructure/scripts/restore.sh

k8s-deploy:
	./infrastructure/scripts/deploy-k8s.sh

k8s-delete:
	kubectl delete -k ./infrastructure/k8s
