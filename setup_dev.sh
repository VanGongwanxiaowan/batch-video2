#!/bin/bash

# Exit on error
set -e

echo "🚀 Setting up BatchShort development environment..."

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3.8+ is required but not installed. Please install it first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [[ "$PYTHON_VERSION" < "3.8" ]]; then
    echo "❌ Python 3.8+ is required but found $PYTHON_VERSION. Please upgrade your Python installation."
    exit 1
fi

# Create and activate virtual environment
echo "🔧 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and setuptools
echo "🔄 Upgrading pip and setuptools..."
pip install --upgrade pip setuptools wheel

# Install development dependencies
echo "📦 Installing development dependencies..."
pip install -e ".[dev]"

# Install pre-commit hooks
echo "🔍 Installing pre-commit hooks..."
pre-commit install

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env <<EOL
# BatchShort Development Environment

# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=batchshort_dev
DB_USER=root
DB_PASSWORD=password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# App
DEBUG=True
ENVIRONMENT=development

# External Services
# AZURE_TTS_KEY=your-azure-tts-key
# AZURE_REGION=your-azure-region
EOL
    echo "✅ .env file created. Please update the values as needed."
fi

echo "✨ Development environment setup complete!"
echo "To activate the virtual environment, run: source venv/bin/activate"
