.PHONY: help bootstrap pipeline-setup pipeline-subset pipeline-full db-create db-load-subset db-load-full web-dev web-build clean

# Default target - show help
help:
	@echo "Deproceduralizer - Common Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make bootstrap          - Set up all tracks from scratch"
	@echo "  make pipeline-setup     - Set up Python environment"
	@echo ""
	@echo "Track A - Pipeline:"
	@echo "  make pipeline-subset    - Run pipeline on subset data"
	@echo "  make pipeline-full      - Run pipeline on full DC Code corpus"
	@echo ""
	@echo "Track B - Database:"
	@echo "  make db-create          - Create database tables"
	@echo "  make db-load-subset     - Load subset data to database"
	@echo "  make db-load-full       - Load full corpus data to database"
	@echo ""
	@echo "Track C - Web:"
	@echo "  make web-dev            - Start Next.js development server"
	@echo "  make web-build          - Build Next.js app for production"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean              - Remove temporary files and state"

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

# Track A - Run pipeline on subset
pipeline-subset:
	@echo "Running pipeline on subset data..."
	./scripts/run_all_subset.sh

# Track A - Run pipeline on full corpus
pipeline-full:
	@echo "Running pipeline on full DC Code corpus..."
	./scripts/run_all_full.sh

# Track B - Create database tables
db-create:
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "❌ ERROR: DATABASE_URL not set. Copy .env.example to .env and fill it in."; \
		exit 1; \
	fi
	@echo "Creating database tables..."
	psql "$$DATABASE_URL" -f dbtools/create_tables.sql
	@echo "✅ Database tables created"

# Track B - Load subset data
db-load-subset:
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "❌ ERROR: DATABASE_URL not set"; \
		exit 1; \
	fi
	@echo "Loading subset data to database..."
	@if [ -f data/outputs/sections_subset.ndjson ]; then \
		. .venv/bin/activate && python dbtools/load_sections.py --input data/outputs/sections_subset.ndjson; \
	else \
		echo "⚠️  No sections_subset.ndjson found. Run 'make pipeline-subset' first."; \
	fi

# Track B - Load full corpus data
db-load-full:
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "❌ ERROR: DATABASE_URL not set"; \
		exit 1; \
	fi
	@echo "Loading full corpus data to database..."
	@echo "This will take a while. All loaders support resume from checkpoints."
	@if [ -f data/outputs/sections.ndjson ]; then \
		. .venv/bin/activate && python dbtools/load_sections.py --input data/outputs/sections.ndjson; \
	else \
		echo "⚠️  No sections.ndjson found. Run 'make pipeline-full' first."; \
	fi

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

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	find . -name "*.state" -type f -delete
	find . -name "*.ckpt" -type f -delete
	find . -name "*.checkpoint" -type f -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -type f -delete
	@echo "✅ Cleaned"
