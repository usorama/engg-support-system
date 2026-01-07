# VPS Remote Access Guide

> **Hostinger VPS**: 72.60.204.156
> **OS**: Ubuntu (Linux)
> **Purpose**: Knowledge Base deployment (Qdrant + Ollama)

---

## Option 1: SSH Terminal (Fastest - Recommended for Development)

### From Terminal

```bash
# Direct SSH
ssh root@72.60.204.156
# Password: t7Zqz&b)AZcQp3)Fc+8J

# Or with sshpass (no password prompt)
sshpass -p 't7Zqz&b)AZcQp3)Fc+8J' ssh root@72.60.204.156
```

### From VS Code (Best for Development)

1. Install **Remote - SSH** extension in VS Code
2. Press `Cmd+Shift+P` → "Remote-SSH: Connect to Host"
3. Add new host:
   ```
   Host kb-vps
     HostName 72.60.204.156
     User root
   ```
4. Select "kb-vps" to connect
5. Enter password when prompted

**Benefits**: Full VS Code editor with terminal, file browser, extensions

### From iTerm2 (Mac)

1. Create new profile
2. Command: `ssh root@72.60.204.156`
3. Save as "KB-VPS"

---

## Option 2: Cockpit (Web-based Admin UI - Easiest)

Cockpit provides a web-based interface for server administration.

### Installation (Run on VPS)

```bash
# SSH into VPS first
ssh root@72.60.204.156

# Install Cockpit
apt update
apt install -y cockpit cockpit-podman cockpit-docker cockpit-machines

# Enable and start Cockpit
systemctl enable --now cockpit.socket

# Open firewall (if UFW is active)
ufw allow 9090/tcp
```

### Access

1. Open browser: `https://72.60.204.156:9090`
2. Accept SSL warning (self-signed cert)
3. Login:
   - Username: `root`
   - Password: `t7Zqz&b)AZcQp3)Fc+8J`

**Features**:
- ✅ System metrics (CPU, RAM, Disk)
- ✅ Docker container management
- ✅ Terminal access
- ✅ Log viewing
- ✅ Service management
- ✅ Network configuration
- ✅ User accounts

---

## Option 3: VNC Server (Full Desktop)

### Install Desktop Environment + VNC

```bash
# SSH into VPS
ssh root@72.60.204.156

# Install lightweight desktop (XFCE) + VNC
apt update
apt install -y xfce4 xfce4-goodies tightvncserver

# Install Firefox (optional, for browsing)
apt install -y firefox

# Set VNC password
vncserver :1
# Enter password when prompted (remember it!)
# Kill the server to configure
vncserver -kill :1
```

### Configure VNC

```bash
# Configure XFCE for VNC
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
startxfce4 &
EOF

chmod +x ~/.vnc/xstartup

# Start VNC server on display :1 (port 5901)
vncserver :1 -geometry 1920x1080 -depth 24
```

### Access from Mac

1. Download VNC Viewer: https://www.realvnc.com/en/connect/download/viewer/
2. Open VNC Viewer
3. Enter: `72.60.204.156:5901`
4. Enter VNC password
5. Full XFCE desktop appears!

### Auto-start VNC on Boot

```bash
# Create systemd service
cat > /etc/systemd/system/vncserver@.service << 'EOF'
[Unit]
Description=VNC Server
After=syslog.target network.target

[Service]
Type=forking
User=root
PAMName=login
PIDFile=/root/.vnc/%H:%i.pid
ExecStartPre=/bin/sh -c '/usr/bin/vncserver -kill :%i > /dev/null 2>&1 || :'
ExecStart=/usr/bin/vncserver :%i -geometry 1920x1080 -depth 24
ExecStop=/usr/bin/vncserver -kill :%i

[Install]
WantedBy=multi-user.target
EOF

# Enable service
systemctl daemon-reload
systemctl enable vncserver@1.service
systemctl start vncserver@1.service
```

### Secure VNC via SSH Tunnel (Recommended)

Instead of exposing VNC directly, tunnel through SSH:

```bash
# On your Mac, create SSH tunnel
ssh -L 5901:localhost:5901 root@72.60.204.156

# In another terminal, open VNC Viewer
# Connect to: localhost:5901
# (This goes through SSH tunnel - encrypted!)
```

---

## Option 4: XRDP (Remote Desktop Protocol)

### Install XRDP + Desktop

```bash
# SSH into VPS
ssh root@72.60.204.156

# Install XRDP and XFCE
apt update
apt install -y xrdp xfce4 xfce4-goodies

# Configure XFCE for XRDP
echo xfce4-session > ~/.xsession

# Enable XRDP
systemctl enable xrdp
systemctl start xrdp

# Allow through firewall
ufw allow 3389/tcp
```

### Access from Mac

1. Download **Microsoft Remote Desktop** from App Store
2. Add new PC:
   - PC name: `72.60.204.156`
   - User account: `root`
   - Password: `t7Zqz&b)AZcQp3)Fc+8J`
3. Connect

---

## Option 5: VS Code Remote (Recommended for Development)

### Setup

1. Install VS Code extension: **Remote - SSH**
2. Configure SSH hosts:

```bash
# On your Mac, create/edit SSH config
mkdir -p ~/.ssh
cat >> ~/.ssh/config << 'EOF'

Host kb-vps
  HostName 72.60.204.156
  User root
  # Optionally, use SSH key for passwordless login
  # IdentityFile ~/.ssh/id_rsa
EOF
```

3. In VS Code:
   - Press `Cmd+Shift+P`
   - "Remote-SSH: Connect to Host"
   - Select "kb-vps"
   - Enter password: `t7Zqz&b)AZcQp3)Fc+8J`

### Features

- ✅ Full VS Code editor on remote files
- ✅ Integrated terminal
- ✅ File explorer
- ✅ Git integration
- ✅ Extensions work on remote
- ✅ Debug remote code

**This is the BEST option for development work!**

---

## Quick Reference

| Method | Best For | Difficulty | GUI |
|--------|----------|------------|-----|
| **SSH Terminal** | Quick commands | ⭐ Easy | ❌ No |
| **VS Code Remote** | Development | ⭐ Easy | ❌ No (but editor) |
| **Cockpit** | Server admin | ⭐ Easy | ✅ Yes (web) |
| **VNC** | Full desktop | ⭐⭐ Medium | ✅ Yes (full) |
| **XRDP** | Windows-style | ⭐⭐ Medium | ✅ Yes (full) |

---

## Recommended Setup

### For Development:
**VS Code Remote SSH** - Full IDE experience with terminal

### For Monitoring/Admin:
**Cockpit** - Web interface to see containers, metrics, logs

### For Visual Desktop:
**VNC + XFCE** - Full Linux desktop when needed

---

## Quick Start Commands

```bash
# 1. SSH in (terminal)
ssh root@72.60.204.156

# 2. Check Docker containers
docker ps
docker logs kb-qdrant --tail 50 -f
docker logs kb-ollama --tail 50 -f

# 3. View resource usage
htop  # Install with: apt install htop

# 4. Check disk usage
df -h
du -sh /data/*

# 5. Restart services
cd /root/Projects/knowledge-base/vps
docker-compose restart
```

---

## Security Tips

1. **Use SSH keys instead of passwords** (recommended):
   ```bash
   # On your Mac, generate SSH key
   ssh-keygen -t ed25519

   # Copy to VPS
   ssh-copy-id root@72.60.204.156

   # Now you can SSH without password!
   ssh root@72.60.204.156
   ```

2. **Enable firewall**:
   ```bash
   ufw enable
   ufw allow ssh
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw allow 6333/tcp  # Qdrant
   ufw allow 11434/tcp # Ollama
   ```

3. **Keep system updated**:
   ```bash
   apt update && apt upgrade -y
   ```

---

## Troubleshooting

### Can't connect via SSH

```bash
# Check if SSH is running
systemctl status ssh

# Restart SSH
systemctl restart ssh

# Check firewall
ufw status
```

### Containers not starting

```bash
# Check Docker status
systemctl status docker

# View container logs
docker logs kb-qdrant
docker logs kb-ollama

# Restart Docker
systemctl restart docker
cd /root/Projects/knowledge-base/vps
docker-compose up -d
```

### VNC connection refused

```bash
# Check if VNC is running
ps aux | grep vnc

# Restart VNC
vncserver -kill :1
vncserver :1 -geometry 1920x1080 -depth 24
```

---

**Created**: 2026-01-06
**VPS**: Hostinger (72.60.204.156)
**Project**: Knowledge Base (rad-engineer-v2)
