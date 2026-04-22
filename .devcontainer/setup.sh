#!/bin/zsh
set -e

# Copy shell configuration
cp .devcontainer/config/.zshrc ~/.zshrc
source ~/.zshrc
mkdir -p ~/.config
cp .devcontainer/config/starship.toml ~/.config/starship.toml

# Rebuild Python virtual environment inside the container
# (A .venv created on the host may have incompatible platform binaries)
rm -rf .venv
uv venv
uv sync || uv pip install -r requirements.txt

# Install Claude Code CLI (native installer, auto-updates)
curl -fsSL https://claude.ai/install.sh | bash

# Configure Claude Code to skip permission prompts inside the container
mkdir -p ~/.claude
cat > ~/.claude/settings.json <<'EOF'
{
  "permissions": {
    "defaultMode": "bypassPermissions"
  }
}
EOF
