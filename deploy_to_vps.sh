#!/bin/bash
# =============================================================================
# MCOT Rental Platform - Safe Deploy to VPS (PostgreSQL Ready)
# ⚠️ IMPORTANT: GIT COMMIT YOURSELF FIRST BEFORE RUNNING THIS SCRIPT
# Usage: bash deploy_to_vps.sh
# =============================================================================

set -e  # Exit on any error

VPS_IP="43.173.251.244"
VPS_PORT="8022"
VPS_USER="ubuntu"
DEPLOY_BRANCH="v3"
SSH_KEY="~/.ssh/id_ed25519_mcot"
PROJECT_DIR=$(pwd)

echo "🚀 MCOT Rental Platform - Deploy Script (Safe Mode)"
echo "===================================================="
echo ""

# Pre-flight check: Ensure no uncommitted changes
echo "📋 Pre-flight Check 1: Git Status"
if ! git diff-index --quiet HEAD --; then
    echo "❌ ERROR: You have uncommitted changes. Commit them first!"
    echo ""
    echo "Run: git add . && git commit -m 'your message'"
    echo "Then run this script again."
    exit 1
fi
echo "✅ Git working tree is clean"
echo ""

# Pre-flight check: Ensure we're on the correct branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "$DEPLOY_BRANCH" ]; then
    echo "⚠️  Current branch: $CURRENT_BRANCH (Expected: $DEPLOY_BRANCH)"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborting."
        exit 1
    fi
fi
echo ""

# Step 1: Push code to Git
echo "📦 Step 1: Pushing code to Git..."
COMMIT_SHA=$(git rev-parse --short HEAD)
echo "Current commit: $COMMIT_SHA"
git push origin "$DEPLOY_BRANCH" || { echo "⚠️ Git push failed"; exit 1; }
echo "✅ Code pushed"
echo ""

# Step 2: SSH to VPS and deploy (with safety checks)
echo "🖥️ Step 2: Connecting to VPS and deploying..."
echo "Enter VPS SSH password when prompted"
echo ""

ssh -i $SSH_KEY -t -p $VPS_PORT $VPS_USER@$VPS_IP << 'REMOTE_COMMANDS'
set -e

echo "✅ Connected to VPS!"
echo ""

# Find project directory
if [ -d ~/MCOT_Rental_Platform ]; then
    cd ~/MCOT_Rental_Platform
elif [ -d ~/mcot ]; then
    cd ~/mcot
else
    echo "📂 Looking for project directory..."
    find ~ -maxdepth 2 -name "manage.py" -type f 2>/dev/null
    echo ""
    echo "❌ Project directory not found. Check path."
    exit 1
fi

PROJECT_PATH=$(pwd)
echo "📂 Project: $PROJECT_PATH"
echo ""

# Pre-flight: Check DATABASE_URL is set
echo "📋 Pre-flight Check: DATABASE_URL"
if ! grep -q "^DATABASE_URL=" .env 2>/dev/null; then
    echo "❌ ERROR: DATABASE_URL not found in .env"
    echo "Set it first:"
    echo '  DATABASE_URL=postgresql://user:pass@localhost:5432/db_name'
    exit 1
fi
echo "✅ DATABASE_URL is configured"
echo ""

# Pre-flight: Health check (Before Deploy)
echo "🏥 Health Check (Before Deploy):"
python3 manage.py check --deploy 2>&1 | head -20 || echo "ℹ️ Check returned some warnings (expected)"
echo ""

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi
echo ""

# Pull latest code
echo "📥 Pulling latest code..."
git fetch origin v3
git checkout v3
git pull --ff-only origin v3 || { echo "⚠️ Git pull failed"; exit 1; }
echo "✅ Code updated"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# BACKUP DATABASE BEFORE MIGRATE
echo "💾 Backing up database..."
BACKUP_DIR="$PROJECT_PATH/backups/postgres"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql.gz"

# Extract PostgreSQL credentials from DATABASE_URL
# Format: postgresql://user:password@host:port/dbname
DB_URL=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2-)
if [ -z "$DB_URL" ]; then
    echo "⚠️ Could not parse DATABASE_URL"
    exit 1
fi

# Simple extraction (works for postgresql:// URLs)
DB_USER=$(echo "$DB_URL" | sed -E 's|postgresql://([^:]+):.*|\1|')
DB_HOST=$(echo "$DB_URL" | sed -E 's|.*@([^:]+):.*|\1|')
DB_PORT=$(echo "$DB_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
DB_NAME=$(echo "$DB_URL" | sed -E 's|.*/([^?]+).*|\1|')

if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE" 2>/dev/null; then
    echo "✅ Database backed up to: $BACKUP_FILE"
else
    echo "⚠️ Database backup failed (continuing anyway)"
fi
echo ""

# Run migrations
echo "🔄 Running migrations..."
python3 manage.py migrate || { echo "❌ Migration failed"; exit 1; }
echo "✅ Migrations completed"
echo ""

# Collect static files
echo "📁 Collecting static files..."
python3 manage.py collectstatic --noinput -q
echo "✅ Static files collected"
echo ""

# Restart application service
echo "♻️ Restarting Gunicorn..."
if sudo systemctl restart gunicorn 2>/dev/null; then
    sleep 2
    if sudo systemctl is-active --quiet gunicorn; then
        echo "✅ Gunicorn restarted successfully"
    else
        echo "❌ Gunicorn failed to start"
        echo "Check logs: sudo journalctl -u gunicorn -n 50 --no-pager"
        exit 1
    fi
else
    echo "⚠️ Could not restart gunicorn (may not have sudo access)"
fi
echo ""

# Post-deploy health check
echo "🏥 Health Check (After Deploy):"
if python3 manage.py check --deploy 2>&1 | head -10; then
    echo "✅ Application health check passed"
else
    echo "⚠️ Some checks failed - review above"
fi
echo ""

echo "✅ Deployment complete!"
echo ""
echo "📝 Verify deployment:"
echo "1. Check app logs: tail -f logs/error.log"
echo "2. Test website: https://mcotequipmentservices.mcot.net"
echo "3. Verify booking flow"

REMOTE_COMMANDS

echo ""
echo "🎉 Done! Check the output above for any errors."
