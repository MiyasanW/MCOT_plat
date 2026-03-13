#!/bin/bash
# =============================================================================
# MCOT Rental Platform - Deploy Google Login to VPS
# เปิด Terminal แล้วรัน: bash deploy_to_vps.sh
# =============================================================================

VPS_IP="43.173.251.244"
VPS_PORT="8022"
VPS_USER="ubuntu"
DEPLOY_BRANCH="v3"
SSH_KEY="~/.ssh/id_ed25519_mcot"
PROJECT_DIR=$(pwd)

echo "🚀 MCOT Rental Platform - Deploy Script"
echo "========================================"
echo ""

# Step 1: Git commit & push
echo "📦 Step 1: Committing and pushing code to Git..."
cd "$PROJECT_DIR"
git add .
git commit -m "feat: setup postgresql and latest updates" 2>/dev/null || echo "Nothing new to commit"
git push origin "$DEPLOY_BRANCH" 2>/dev/null || echo "⚠️ Git push failed - you may need to push manually"
echo ""

# Step 2: SSH to VPS and deploy
echo "🖥️ Step 2: Connecting to VPS and deploying..."
echo "กรุณากรอกรหัสผ่าน VPS เมื่อถูกถาม"
echo ""

ssh -i $SSH_KEY -t -p $VPS_PORT $VPS_USER@$VPS_IP << REMOTE_COMMANDS
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
    echo "❌ ไม่พบโฟลเดอร์โปรเจกต์ กรุณาระบุ path ที่ถูกต้อง"
    exit 1
fi

echo "📂 Project directory: $(pwd)"
echo ""

# Pull latest code
echo "📥 Pulling latest code..."
git fetch origin
git checkout $DEPLOY_BRANCH
git pull --ff-only origin $DEPLOY_BRANCH || echo "⚠️ Git pull failed"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

pip install -r requirements.txt
echo ""

# Run migrations
echo "🔄 Running migrations..."
python3 manage.py migrate
echo ""

# Collect static files
echo "📁 Collecting static files..."
python3 manage.py collectstatic --noinput 2>/dev/null || true
echo ""

echo "♻️ Restarting Gunicorn..."
sudo systemctl restart gunicorn
sudo systemctl is-active gunicorn
echo ""

echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Go to Django Admin → Sites → Edit site domain to match your VPS domain"
echo "2. Go to Django Admin → Social Applications → Add Google OAuth credentials"
echo "3. Verify website and login flow"

REMOTE_COMMANDS

echo ""
echo "🎉 Done! Check the output above for any errors."
