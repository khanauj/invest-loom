.PHONY: dev backend frontend install

# Default target
all: dev

# Run both backend and frontend (Requires running in separate terminals or using 'make serve' on Unix)
dev:
	@echo "========================================"
	@echo "  To run both services simultaneously:"
	@echo "  On Windows: Double-click 'run.bat' or run it in terminal"
	@echo "  On Mac/Linux: Run 'make serve'"
	@echo "========================================"

serve:
	@echo "Starting both services (Unix only)..."
	@trap 'kill %1' SIGINT; \
	python main.py api & \
	cd frontend && npm run dev

backend:
	@echo "Starting FastAPI Backend on port 8000..."
	python main.py api

frontend:
	@echo "Starting Next.js Frontend on port 3000..."
	cd frontend && npm run dev

install:
	@echo "Installing Backend dependencies..."
	pip install -r requirements.txt
	@echo "Installing Frontend dependencies..."
	cd frontend && npm install
