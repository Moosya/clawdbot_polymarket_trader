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

### How to Push Changes

```bash
# 1. Clone fresh into /tmp (you own this as root)
cd /tmp && git clone https://github.com/Moosya/clawdbot_polymarket_trader.git repo

# 2. Copy all changed files from workspace
cd /workspace
git diff --name-only HEAD > /tmp/changed_files.txt
git ls-files --others --exclude-standard >> /tmp/changed_files.txt

# 3. Copy files to the temp repo
cd /tmp/repo
while IFS= read -r file; do
  if [ -f "/workspace/$file" ]; then
    mkdir -p "$(dirname "$file")"
    cp "/workspace/$file" "$file"
  fi
done < /tmp/changed_files.txt

# 4. Commit and push
git add .
git commit -m "Update from workspace"
git push origin master
```

### Quick Helper Script

Create this as needed:

```bash
#!/bin/bash
# /workspace/git-push-helper.sh

set -e

echo "🦀 Cloning repo to /tmp..."
cd /tmp && rm -rf repo 2>/dev/null || true
git clone https://github.com/Moosya/clawdbot_polymarket_trader.git repo

echo "🦀 Syncing workspace files..."
rsync -av --exclude='.git' /workspace/ /tmp/repo/

echo "🦀 Committing changes..."
cd /tmp/repo
git add .
git status

read -p "Commit message: " msg
git commit -m "$msg"

echo "🦀 Pushing to origin..."
git push origin master

echo "✅ Done! Cleaning up..."
rm -rf /tmp/repo
```

### Alternative: Simple Rsync Method

```bash
# One-liner to sync and push
cd /tmp && rm -rf repo && git clone https://github.com/Moosya/clawdbot_polymarket_trader.git repo && rsync -av --exclude='.git' /workspace/ /tmp/repo/ && cd /tmp/repo && git add . && git commit -m "Update from workspace" && git push origin master && rm -rf /tmp/repo
```

---

**Note:** This is a workaround. The "proper" fix would be running the sandbox container as `user: "1000:1000"` in docker-compose, but we're avoiding that to prevent unknown side effects.

**Last Updated:** 2026-02-06
