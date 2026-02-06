#!/usr/bin/env bash
set -euo pipefail

# Small helper to deploy the repo to Render using the Render CLI.
# Requires: `render` CLI installed and `render login` already executed (API key present).

echo "Deploying services from render.yaml..."

if ! command -v render >/dev/null 2>&1; then
  echo "render CLI not found. Install from https://render.com/docs/cli"
  exit 1
fi

# Validate manifest
render services sync --dry-run || true

echo "To deploy for real, run:"
echo "  render services sync"
