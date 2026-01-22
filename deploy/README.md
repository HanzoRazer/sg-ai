# SG-AI Deployment

## Device Installation

### Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS (64-bit)
- Python 3.11+
- uv package manager

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install from Bundle

```bash
# Extract bundle
sudo mkdir -p /opt/sg-ai
sudo tar -xzf sg-ai-bundle-*.tar.gz -C /opt/sg-ai

# Change to install directory
cd /opt/sg-ai

# Install Python dependencies
uv sync --frozen

# Create data directory
sudo mkdir -p /opt/sg-ai/data
sudo chown sg:sg /opt/sg-ai/data
```

### Create Service User

```bash
sudo useradd -r -s /bin/false sg
sudo chown -R sg:sg /opt/sg-ai
```

### Install systemd Service

```bash
sudo cp /opt/sg-ai/deploy/systemd/sg-engine.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sg-engine
sudo systemctl start sg-engine
```

### Check Status

```bash
sudo systemctl status sg-engine
journalctl -u sg-engine -f
```

### Access UI

Open `http://<pi-ip>:8000/` in a browser on the same network.

## Manual Run (Development)

```bash
cd /opt/sg-ai/packages/sg-engine
uv run sgc run --reload
```

## Update

```bash
# Stop service
sudo systemctl stop sg-engine

# Extract new bundle
sudo tar -xzf sg-ai-bundle-NEW.tar.gz -C /opt/sg-ai

# Sync dependencies
cd /opt/sg-ai && uv sync --frozen

# Restart
sudo systemctl start sg-engine
```
