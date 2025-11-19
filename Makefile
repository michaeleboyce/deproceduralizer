.PHONY: help bootstrap pipeline-setup pipeline-small pipeline-medium pipeline-large db-load-small db-load-medium db-load-large web-dev web-build clean clean-state status quick-small quick-medium quick-large

# Default target - show help
help:
	@echo "Deproceduralizer - Common Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make bootstrap          - Set up all tracks from scratch"
	@echo "  make pipeline-setup     - Set up Python environment"
	@echo ""
	@echo "Track A - Pipeline:"
	@echo "  make pipeline-small     - Run pipeline on small corpus (Titles 1-2)"
	@echo "  make pipeline-medium    - Run pipeline on medium corpus (Titles 1-10)"
	@echo "  make pipeline-large     - Run pipeline on large corpus (all ~50 titles)"
	@echo ""
	@echo "Track B - Database:"
	@echo "  make db-load-small      - Load small corpus data to database"
	@echo "  make db-load-medium     - Load medium corpus data to database"
	@echo "  make db-load-large      - Load large corpus data to database"
	@echo ""
	@echo "Track C - Web:"
	@echo "  make web-dev            - Start Next.js development server"
	@echo "  make web-build          - Build Next.js app for production"
	@echo ""
	@echo "Quick Workflows:"
	@echo "  make quick-small        - Run pipeline + load database (small)"
	@echo "  make quick-medium       - Run pipeline + load database (medium)"
	@echo "  make quick-large        - Run pipeline + load database (large)"
	@echo ""
	@echo "Utilities:"
	@echo "  make status             - Show pipeline and database status"
	@echo "  make clean              - Remove Python cache files"
	@echo "  make clean-state        - Remove pipeline checkpoints"

# Bootstrap entire project
bootstrap: pipeline-setup db-create
	@echo "✅ All tracks ready to start work"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and fill in DATABASE_URL"
	@echo "  2. Verify Ollama is running: ollama list"
	@echo "  3. Clone DC XML: git clone https://github.com/DCCouncil/law-xml.git data/raw/dc-law-xml"
	@echo "  4. See PROJECT_TODO.md for detailed tasks"

# Track A - Pipeline setup
pipeline-setup:
	@echo "Setting up Python environment..."
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -r pipeline/requirements.txt
	@echo "✅ Python environment ready"
	@echo "Activate with: source .venv/bin/activate"

# Track A - Run pipeline on small corpus
pipeline-small:
	./scripts/run-pipeline.sh --corpus=small

# Track A - Run pipeline on medium corpus
pipeline-medium:
	./scripts/run-pipeline.sh --corpus=medium

# Track A - Run pipeline on large corpus
pipeline-large:
	./scripts/run-pipeline.sh --corpus=large

# Track B - Load small corpus data
db-load-small:
	./scripts/load-database.sh --corpus=small

# Track B - Load medium corpus data
db-load-medium:
	./scripts/load-database.sh --corpus=medium

# Track B - Load large corpus data
db-load-large:
	./scripts/load-database.sh --corpus=large

# Quick workflows - pipeline + database in one command
quick-small: pipeline-small db-load-small
	@echo "✅ Small corpus pipeline + database load complete"

quick-medium: pipeline-medium db-load-medium
	@echo "✅ Medium corpus pipeline + database load complete"

quick-large: pipeline-large db-load-large
	@echo "✅ Large corpus pipeline + database load complete"

# Track C - Development server
web-dev:
	@if [ ! -d "apps/web/node_modules" ]; then \
		echo "Installing web dependencies..."; \
		cd apps/web && pnpm install; \
	fi
	cd apps/web && pnpm dev

# Track C - Production build
web-build:
	@if [ ! -d "apps/web/node_modules" ]; then \
		echo "Installing web dependencies..."; \
		cd apps/web && pnpm install; \
	fi
	cd apps/web && pnpm build

# Utilities - Clean Python cache files
clean:
	@echo "Cleaning Python cache files..."
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -type f -delete
	@echo "✅ Cleaned"

# Utilities - Clean pipeline checkpoints
clean-state:
	./scripts/clean-state.sh

# Utilities - Show pipeline and database status
status:
	./scripts/status.sh
