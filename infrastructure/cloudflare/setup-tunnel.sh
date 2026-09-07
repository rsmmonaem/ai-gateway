#!/usr/bin/env bash
set -e

echo "=== Cloudflare Tunnel Setup for Mac mini M4 AI Gateway ==="

# 1. Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "Installing cloudflared via Homebrew..."
    brew install cloudflared
fi

echo "cloudflared is installed: $(cloudflared --version)"

# 2. Login to Cloudflare
echo "Step 1: Authenticate with Cloudflare..."
echo "Running 'cloudflared tunnel login' (a browser window will open to select your domain)..."
cloudflared tunnel login

# 3. Create Tunnel
TUNNEL_NAME="mac-m4-ai-gateway"
echo "Step 2: Creating tunnel '$TUNNEL_NAME'..."
cloudflared tunnel create "$TUNNEL_NAME"

echo ""
echo "Step 3: Note the Tunnel ID printed above."
echo "Copy infrastructure/cloudflare/config.yml to ~/.cloudflared/config.yml"
echo "and update YOUR_CLOUDFLARE_TUNNEL_UUID with your actual tunnel ID."
echo ""
echo "Step 4: Route your DNS hostname to the tunnel:"
echo "cloudflared tunnel route dns $TUNNEL_NAME api.yourdomain.com"
echo ""
echo "Step 5: Test the tunnel run:"
echo "cloudflared tunnel run $TUNNEL_NAME"
echo ""
echo "Step 6: Install as a permanent macOS system service:"
echo "sudo cloudflared service install"
echo "sudo launchctl start com.cloudflare.cloudflared"
echo "=== Cloudflare Tunnel Setup Ready ==="
