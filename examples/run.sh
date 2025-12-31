#!/usr/bin/env bash
# Development server launcher for fin-infra-template

set -e

# Get script directory (examples/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables from .env if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
  echo "Loading environment variables from $SCRIPT_DIR/.env"
  set -a  # Automatically export all variables
  source "$SCRIPT_DIR/.env"
  set +a  # Stop auto-exporting
fi

# Default port
PORT=${API_PORT:-8001}

echo " Starting fin-infra-template server on port $PORT..."
echo "📖 OpenAPI docs: http://localhost:$PORT/docs"
echo " Metrics: http://localhost:$PORT/metrics"
echo "🏥 Health: http://localhost:$PORT/_health"
echo ""

# Run with uvicorn (--app-dir tells uvicorn where to find the package)
poetry run uvicorn --app-dir src fin_infra_template.main:app \
  --host "${API_HOST:-0.0.0.0}" \
  --port "$PORT" \
  --reload \
  --log-level info
