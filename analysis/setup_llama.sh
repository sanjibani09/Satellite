#!/bin/bash
# setup_llama.sh - Setup Llama models for GeoGPT

echo "🦙 Setting up Llama for GeoGPT"
echo "================================"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "📦 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✅ Ollama installed"
else
    echo "✅ Ollama already installed"
fi

# Start Ollama service (if not running)
echo ""
echo "🚀 Starting Ollama service..."
if pgrep -x "ollama" > /dev/null; then
    echo "✅ Ollama is already running"
else
    nohup ollama serve > ollama.log 2>&1 &
    sleep 3
    echo "✅ Ollama service started"
fi

# Pull Llama model
echo ""
echo "📥 Downloading Llama 3.1 (8B) model..."
echo "   (This may take a few minutes - ~4.7GB)"
ollama pull llama3.1:8b

if [ $? -eq 0 ]; then
    echo "✅ Llama 3.1 model downloaded"
else
    echo "❌ Failed to download model"
    exit 1
fi

# Verify installation
echo ""
echo "🧪 Testing installation..."
RESPONSE=$(curl -s http://localhost:11434/api/tags)

if [ -n "$RESPONSE" ]; then
    echo "✅ Ollama API is responsive"
    echo ""
    echo "📋 Available models:"
    echo "$RESPONSE" | grep -o '"name":"[^"]*"' | cut -d'"' -f4
else
    echo "❌ Ollama API not responding"
    exit 1
fi

echo ""
echo "================================"
echo "✅ Setup Complete!"
echo ""
echo "📝 Next steps:"
echo "1. Test LLM: python llm_interface.py"
echo "2. Start API: python analysis/analysis_api_with_llm.py"
echo "3. Test API: python test_llm_api.py"
echo ""
echo "🦙 Llama is ready for GeoGPT!"