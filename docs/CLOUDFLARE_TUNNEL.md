# Cloudflare Tunnel Configuration Guide

Expose your Mac mini M4 AI Gateway securely to the public internet without opening router ports, configuring port forwarding, or exposing private backend model engines.

---

## Security Architecture

```
Internet Users
     │
     ▼ (HTTPS via TLS 1.3)
Cloudflare Global Anycast Edge
     │
     │ Encrypted Tunnel (Outbound connection only)
     ▼
Mac mini M4 Firewall
     │
     ▼ (Traffic terminated locally)
cloudflared daemon
     │
     ▼ (http://127.0.0.1:8000 only)
AI Model Gateway
     │
     ▼ (Local Unix/TCP sockets only, strictly private)
[MLX Server :8081]  [Ollama Server :11434]  [llama-server :8082]
```

---

## Setup Steps

### Step 1: Install cloudflared
```bash
brew install cloudflared
```

### Step 2: Authenticate with Cloudflare
```bash
cloudflared tunnel login
```
This opens your browser. Select your Cloudflare domain.

### Step 3: Create the Tunnel
```bash
cloudflared tunnel create mac-m4-gateway
```
Save the returned Tunnel UUID.

### Step 4: Configure the Ingress
Copy and edit the configuration:
```bash
cp infrastructure/cloudflare/config.yml ~/.cloudflared/config.yml
```
Replace `YOUR_CLOUDFLARE_TUNNEL_UUID` with your actual tunnel UUID.

### Step 5: Route DNS to Tunnel
```bash
cloudflared tunnel route dns mac-m4-gateway api.yourdomain.com
```

### Step 6: Test and Install as macOS Daemon
```bash
# Test run
cloudflared tunnel run mac-m4-gateway

# Install as permanent launchd service (runs on boot)
sudo cloudflared service install
sudo launchctl start com.cloudflare.cloudflared
```

Your Gateway is now publicly reachable at `https://api.yourdomain.com/v1`!
