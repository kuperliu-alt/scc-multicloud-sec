#!/bin/bash
# ==============================================================================
# Universal Project Workspace Bootstrap Script
# ==============================================================================
set -euo pipefail

echo "================================================================="
echo "  🚀 Bootstrapping Universal Project Workspace"
echo "================================================================="

# 1. Ensure tmp & .gcloud directories exist with isolation guarantees
mkdir -p tmp .gcloud
touch tmp/.gitkeep

# 2. Initialize Git repository if not already initialized
if [ ! -d ".git" ]; then
  echo "📦 Initializing local Git repository..."
  git init -q
  echo "✅ Git repository initialized."
else
  echo "ℹ️  Git repository already initialized."
fi

# 3. Create .env from .env.example if not present
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "✅ Created .env from .env.example."
fi

# 4. Configure direnv if installed
if command -v direnv &> /dev/null; then
  direnv allow .
  echo "✅ direnv configured and allowed."
else
  echo "ℹ️  Notice: direnv is not installed. You can manually load environment variables via 'source .envrc' or 'source .env'."
fi

echo "================================================================="
echo "✅ Universal Workspace Initialized Successfully!"
echo "Features enabled:"
echo "  • Physical Session Isolation for gcloud (.gcloud directory)"
echo "  • Scratch script isolation in tmp/"
echo "  • Multi-Agent collaboration rules in .agents/AGENTS.md"
echo "Next steps:"
echo "  1. Review and customize .env as needed"
echo "  2. (Optional) Run 'gcloud auth login' for isolated GCP authentication"
echo "================================================================="
