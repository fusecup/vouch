#!/bin/bash
set -e

echo "[ENTRYPOINT] Starting dependency setup..."

# Ensure we're in the right directory
cd /code/src

# Check if virtual environment needs to be created or updated
if [ ! -f "/code/src/.venv/pyvenv.cfg" ]; then
    echo "[ENTRYPOINT] Creating virtual environment..."
    uv venv
    echo "[ENTRYPOINT] Virtual environment created successfully"
else
    echo "[ENTRYPOINT] Virtual environment already exists"
fi

# Check if dependencies need to be installed/updated
if [ ! -f "/code/src/.venv/.deps_installed" ] || [ "/code/src/pyproject.toml" -nt "/code/src/.venv/.deps_installed" ] || [ "/code/src/uv.lock" -nt "/code/src/.venv/.deps_installed" ]; then
    echo "[ENTRYPOINT] Installing/updating dependencies..."
    if [ "${ENV}" = "dev" ]; then
        echo "[ENTRYPOINT] Installing development dependencies"
        uv sync --frozen --dev
    else
        echo "[ENTRYPOINT] Installing production dependencies"
        uv sync --frozen --no-dev
    fi
    touch /code/src/.venv/.deps_installed
    echo "[ENTRYPOINT] Dependencies installed successfully"
else
    echo "[ENTRYPOINT] Dependencies are up to date"
fi

# Verify Django is available
echo "[ENTRYPOINT] Verifying Django installation..."
if python -c "import django; print(f'Django {django.get_version()} is available')"; then
    echo "[ENTRYPOINT] Django verification successful"
else
    echo "[ENTRYPOINT] ERROR: Django is not available!"
    echo "[ENTRYPOINT] Checking virtual environment..."
    which python
    python --version
    pip list | grep -i django || echo "Django not found in pip list"
    exit 1
fi

echo "[ENTRYPOINT] Setup complete. Starting main command: $@"

# Execute the original command
exec "$@"
