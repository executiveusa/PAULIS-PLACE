#!/bin/bash
# scripts/setup_cloudflare_tunnel.sh
# Sets up Cloudflare Tunnel on the VPS to get a free HTTPS URL for the backend
# This resolves Mixed Content errors when the frontend (HTTPS) calls the backend

set -e

echo "=========================================="
echo "  Cloudflare Tunnel Setup for PAULIS-PLACE"
echo "=========================================="

# 1. Install cloudflared if not present
if ! command -v cloudflared &>/dev/null; then
    echo "[1/5] Installing cloudflared..."
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
    chmod +x /usr/local/bin/cloudflared
    echo "  cloudflared installed: $(cloudflared --version)"
else
    echo "[1/5] cloudflared already installed: $(cloudflared --version)"
fi

# 2. Check if Cloudflare Tunnel token is provided
TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN:-""}

if [ -z "$TUNNEL_TOKEN" ]; then
    echo ""
    echo "⚠️  CLOUDFLARE_TUNNEL_TOKEN not set in .env"
    echo ""
    echo "To get a free HTTPS URL for your backend:"
    echo "1. Go to https://one.dash.cloudflare.com/"
    echo "2. Create a free Cloudflare account (if you don't have one)"
    echo "3. Go to Zero Trust → Networks → Tunnels → Create a tunnel"
    echo "4. Choose 'Self-hosted' → give it a name (e.g., 'paulis-place-backend')"
    echo "5. Copy the tunnel token"
    echo "6. Add it to your .env file: CLOUDFLARE_TUNNEL_TOKEN=your-token-here"
    echo "7. Run this script again: bash scripts/setup_cloudflare_tunnel.sh"
    echo ""
    echo "Alternatively, you can run cloudflared interactively:"
    echo "  cloudflared tunnel login"
    echo "  cloudflared tunnel create paulis-place-backend"
    echo "  cloudflared tunnel route dns paulis-place-backend your-domain.com"
    exit 0
fi

# 3. Configure cloudflared
echo "[3/5] Configuring cloudflared..."
mkdir -p /root/.cloudflared

# Write tunnel token
echo "$TUNNEL_TOKEN" > /root/.cloudflared/tunnel-token.txt
chmod 600 /root/.cloudflared/tunnel-token.txt

# Write config
cat > /root/.cloudflared/config.yml << EOF
tunnel: paulis-place-backend
credentials-file: /root/.cloudflared/tunnel-token.txt
ingress:
  - hostname: paulis-place-backend.your-domain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

echo "  Config written to /root/.cloudflared/config.yml"

# 4. Create systemd service
echo "[4/5] Creating systemd service..."
cat > /etc/systemd/system/cloudflared.service << EOF
[Unit]
Description=Cloudflare Tunnel for PAULIS-PLACE Backend
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/cloudflared tunnel run paulis-place-backend
Restart=always
RestartSec=5
Environment=CLOUDFLARE_TUNNEL_TOKEN=${TUNNEL_TOKEN}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cloudflared
systemctl start cloudflared

echo "  cloudflared service started"

# 5. Wait and verify
echo "[5/5] Verifying tunnel..."
sleep 5

if systemctl is-active --quiet cloudflared; then
    echo "  ✅ cloudflared is running!"
    echo ""
    echo "Your backend should now be accessible at:"
    echo "  https://paulis-place-backend.your-domain.com"
    echo ""
    echo "Update your .env:"
    echo "  NEXT_PUBLIC_API_URL=https://paulis-place-backend.your-domain.com"
    echo ""
    echo "Then redeploy the frontend."
else
    echo "  ❌ cloudflared failed to start"
    echo "  Check logs: journalctl -u cloudflared -f"
    exit 1
fi

echo "=========================================="
echo "  Setup Complete"
echo "=========================================="
