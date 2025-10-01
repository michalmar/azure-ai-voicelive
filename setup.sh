#!/bin/bash

echo "🎙️  Azure AI Voice Live Assistant - Quick Start Setup"
echo "=================================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your AZURE_VOICELIVE_API_KEY"
    echo ""
    read -p "Press Enter after you've added your API key to .env..."
fi

# Check if Docker is installed
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo ""
    echo "🐳 Docker detected! Choose deployment option:"
    echo "  1) Docker Compose (Recommended)"
    echo "  2) Local Development"
    read -p "Enter choice (1 or 2): " choice
    
    if [ "$choice" = "1" ]; then
        echo ""
        echo "🚀 Starting services with Docker Compose..."
        docker-compose up --build
        exit 0
    fi
fi

# Local development setup
echo ""
echo "💻 Setting up for local development..."
echo ""

# Backend setup
echo "🔧 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
fi

cd ..

# Frontend setup
echo ""
echo "🎨 Setting up frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

if [ ! -f .env.local ]; then
    cp .env.example .env.local
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Terminal 1 - Start backend:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m uvicorn app.main:app --reload"
echo ""
echo "2. Terminal 2 - Start frontend:"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "3. Open browser at http://localhost:3000"
echo ""
echo "🎉 Enjoy your voice assistant!"
