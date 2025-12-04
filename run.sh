#!/bin/bash
# Setup and run the Diabetes Medicine & Insurance Comparison Tool

set -e  # exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Setting up Diabetes Medicine & Insurance Tool...${NC}"

# Step 1: Create virtualenv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}📦 Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Step 2: Activate virtualenv
echo -e "${BLUE}✨ Activating virtualenv...${NC}"
source .venv/bin/activate

# Step 3: Upgrade pip
echo -e "${BLUE}⬆️  Upgrading pip, setuptools, wheel...${NC}"
python -m pip install --upgrade pip setuptools wheel --quiet

# Step 4: Install dependencies with force-reinstall to avoid binary incompatibility
echo -e "${BLUE}📚 Installing dependencies (numpy, pandas, Flask, tabulate)...${NC}"
python -m pip install --no-cache-dir --force-reinstall \
    numpy==1.26.4 \
    pandas==2.2.2 \
    tabulate==0.8.9 \
    Flask \
    gunicorn \
    --quiet

# Step 5: Start Flask app
echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "${GREEN}🚀 Starting Flask app on http://127.0.0.1:5000${NC}"
echo -e "${BLUE}Press Ctrl+C to stop the server.${NC}\n"

python app.py
