.PHONY: help setup dev run test docker-up docker-down cli backup restore

help:
	@echo "AI Model Gateway Commands (Mac mini M4):"
	@echo "  make setup         Run full macOS Apple Silicon setup script"
	@echo "  make run           Start the Gateway locally with uvicorn (Port 8000)"
	@echo "  make test          Execute automated pytest test suite"
	@echo "  make docker-up     Start PostgreSQL, Redis, and Gateway via Docker"
	@echo "  make docker-down   Stop Docker containers"
	@echo "  make run-kimi      Launch Kimi 7B on MLX-LM with Metal acceleration"
	@echo "  make run-ollama    Launch Ollama server with Qwen 2.5 7B"
	@echo "  make cli           Run Gateway administration CLI"

setup:
	./infrastructure/scripts/setup-mac-m4.sh

run:
	cd backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	cd backend && pytest -v tests/

docker-up:
	cd infrastructure && docker compose up -d --build

docker-down:
	cd infrastructure && docker compose down

run-kimi:
	./infrastructure/scripts/run-mlx-kimi.sh

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
