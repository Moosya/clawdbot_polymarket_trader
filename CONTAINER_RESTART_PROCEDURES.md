# Container Restart Procedures

## Git Push Workaround (UID Mismatch Issue)

**Problem:** 
- Workspace `/workspace` is owned by UID 1000 (host clawdbot user)
- Container runs as root (UID 0)
- Git blocks push operations due to ownership mismatch
- Container root filesystem is read-only, can't persist `safe.directory` config

**Solution:**
Use /tmp as a temporary git workspace for push operations.

### When Container Restarts

This procedure needs to be done fresh each session because /tmp is ephemeral.

### How to Push Changes (From Container) ✅ WORKING

**Prerequisites:** 
- GitHub token is stored in `/workspace/.env` as `GITHUB_TOKEN`
- Token is protected in .env (gitignored) - don't commit it to the repo!

```bash
# Set git identity (needed in /tmp since HOME is read-only)
export HOME=/tmp
git config --global user.email "clawdbot@polymarket.bot" 2>/dev/null || true
git config --global user.name "Krabby" 2>/dev/null || true

# Load GitHub token from .env
GITHUB_TOKEN=$(grep GITHUB_TOKEN /workspace/.env | cut -d'=' -f2)

# 1. Clone fresh into /tmp (you own this as root)
cd /tmp && rm -rf repo 2>/dev/null || true
git clone https://github.com/Moosya/clawdbot_polymarket_trader.git repo

# 2. Set remote URL with token for push access
cd /tmp/repo
git remote set-url origin https://${GITHUB_TOKEN}@github.com/Moosya/clawdbot_polymarket_trader.git

# 3. Copy changed files from workspace
cp /workspace/CONTAINER_RESTART_PROCEDURES.md /tmp/repo/
# (or use rsync for all files: rsync -av --exclude='.git' /workspace/ /tmp/repo/)

# 4. Commit and push
git add .
git commit -m "Update from workspace"
git push origin master

echo "✅ Successfully pushed to GitHub!"
```

### Quick Commit & Push Script (Container) ✅

```bash
#!/bin/bash
# git-push-helper.sh - Complete workflow from container

set -e

export HOME=/tmp
git config --global user.email "clawdbot@polymarket.bot" 2>/dev/null || true
git config --global user.name "Krabby" 2>/dev/null || true

# Load GitHub token
GITHUB_TOKEN=$(grep GITHUB_TOKEN /workspace/.env | cut -d'=' -f2)

cd /tmp && rm -rf repo 2>/dev/null || true
echo "🦀 Cloning repo..."
git clone https://github.com/Moosya/clawdbot_polymarket_trader.git repo

cd /tmp/repo
echo "🦀 Setting up authenticated remote..."
git remote set-url origin https://${GITHUB_TOKEN}@github.com/Moosya/clawdbot_polymarket_trader.git

echo "🦀 Syncing workspace files..."
rsync -av --exclude='.git' /workspace/ /tmp/repo/

echo "🦀 Committing changes..."
git add .
git status --short
git commit -m "${1:-Update from container workspace}"

echo "🦀 Pushing to GitHub..."
git push origin master

echo ""
echo "✅ Successfully pushed to GitHub!"
rm -rf /tmp/repo
```

**Usage:**
```bash
bash /workspace/git-push-helper.sh "Your commit message"
```

---

**Note:** This is a workaround. The "proper" fix would be running the sandbox container as `user: "1000:1000"` in docker-compose, but we're avoiding that to prevent unknown side effects.

**Last Updated:** 2026-02-06
