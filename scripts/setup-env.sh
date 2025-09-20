#!/bin/bash
# SCP MCP Server - Environment Setup Script
# This script helps you set up your local environment configuration

set -e

echo "🔧 SCP MCP Server - Environment Setup"
echo "======================================"

# Check if .env.local already exists
if [ -f ".env.local" ]; then
    echo "⚠️  .env.local already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled. Existing .env.local preserved."
        exit 1
    fi
fi

# Copy template to local
echo "📋 Copying .env.template to .env.local..."
cp .env.template .env.local

echo "✅ Created .env.local from template"
echo ""
echo "🚀 Next Steps:"
echo "1. Edit .env.local to add your personal settings:"
echo "   - HuggingFace token (HF_TOKEN=hf_your_token_here)"
echo "   - API keys for OpenAI/Anthropic if needed"
echo "   - Custom paths and performance settings"
echo ""
echo "2. The models directory will be created at: ./models"
echo "   (You can change this by editing HUGGINGFACE_HUB_CACHE in .env.local)"
echo ""
echo "3. See ENV_README.md for detailed configuration options"
echo ""
echo "📝 Example configuration files:"
echo "   - .env.template      (base defaults, committed to git)"
echo "   - .env.example       (documented examples, committed to git)"
echo "   - .env.local.example (personal settings template, gitignored)"
echo "   - .env.local         (your settings, gitignored)"
echo ""
echo "🔐 Remember: Never commit .env.local or any file with real API keys!"
