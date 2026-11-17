# Session Recipe: Merge kubuntux unlock-suite into local

## Context
Two copies of `universal-unlock-suite`: local at `/home/lin/Documents/universal-unlock-suite/`
and kubuntux at `/media/kubuntux/DEVELOPMENT1/unlock-suite/` (accessed via SSH as root@100.93.75.87).

Local had extra deployment files (Dockerfile, nginx, celery, migrations, windows_exploits).
Kubuntux had extra functional modules (AI, organized exploits, WebADB, FRP research).

## Step-by-step

```bash
# 1. Stash local changes (including untracked files)
cd /home/lin/Documents/universal-unlock-suite
git stash --include-untracked

# 2. Rsync from kubuntux to local (--delete removes local-only files!)
rsync -avz --delete \
  --exclude='.git/' --exclude='venv/' --exclude='__pycache__/' \
  --exclude='node_modules/' --exclude='.DS_Store' \
  root@100.93.75.87:/media/kubuntux/DEVELOPMENT1/unlock-suite/ \
  /home/lin/Documents/universal-unlock-suite/

# 3. Restore local-only files from stash
git stash pop
# If conflict: keep remote version (functional code), drop stash
# git checkout . && git stash drop

# 4. Fix git safe.directory if needed (remote repo owned by different user)
git config --global --add safe.directory /home/lin/Documents/universal-unlock-suite

# 5. Verify imports
cd /home/lin/Documents/universal-unlock-suite
python3 -c "
import sys; sys.path.insert(0, '.')
from backend.exploits.integrated_android import IntegratedAndroidExploitSuite
from backend.exploits.ios.icloud_bypass import iCloudBypass
from backend.exploits.mdm.mdm_remover import MDMRemover
from backend.exploits.windows_exploits import WindowsExploitSuite
from backend.ai.unlock_ai import UnlockAI
print('All imports OK')
"

# 6. Update .gitignore to cover both
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
venv/
.venv/
.env
dist/
node_modules/
.DS_Store
*.db
*.sqlite
*.sqlite3
EOF
```

## Key Differences Found
- Kubuntux had `backend/app/main.py` completely rewritten (v2.0 with factory pattern)
- Kubuntux had organized exploit modules (android/, ios/, mdm/, core/, ai/)
- Local had migration scripts, celery config, Dockerfiles, nginx config
- Same git commit history (both from same origin commit)
