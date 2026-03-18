# Deploy to VPS with PostgreSQL — Complete Guide

This guide covers the complete process to deploy MCOT Equipment Service to production VPS with PostgreSQL database.

---

## Prerequisites

✅ **Local machine**:
- Git repository with clean working tree
- SSH key registered on VPS (`~/.ssh/id_ed25519_mcot`)
- All changes committed to branch `v3`

✅ **VPS** (one-time setup):
- Ubuntu 20.04+ with sudo access
- PostgreSQL 12+
- Python 3.9+
- Gunicorn service configured
- Nginx reverse proxy configured

---

## Step 1: VPS One-Time Setup (PostgreSQL + Application User)

Run these commands once on the VPS to prepare the database and application environment.

### 1.1 Create PostgreSQL Database and User

```bash
ssh -p 8022 ubuntu@43.173.251.244

# Switch to postgres user
sudo -u postgres psql

# Create database
CREATE DATABASE mcot_rental_db;

# Create app user with strong password
CREATE USER mcot_user WITH PASSWORD 'your_strong_password_here_change_me';

# Grant all privileges
ALTER ROLE mcot_user SET client_encoding TO 'utf8';
ALTER ROLE mcot_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE mcot_user SET default_transaction_deferrable TO on;
ALTER ROLE mcot_user SET default_transaction_read_only TO off;
GRANT ALL PRIVILEGES ON DATABASE mcot_rental_db TO mcot_user;

# Exit psql
\q
```

### 1.2 Create `.env` File on VPS

```bash
cd ~/MCOT_Rental_Platform

# Copy template
cp .env.example .env

# Edit .env with production values
nano .env
```

**Required environment variables**:

```bash
# Django
DEBUG=False
SECRET_KEY=your-secret-key-change-this-to-something-random
ALLOWED_HOSTS=mcotequipmentservices.mcot.net,www.mcotequipmentservices.mcot.net

# DATABASE — PostgreSQL (Use this format exactly)
DATABASE_URL=postgresql://mcot_user:your_strong_password_here_change_me@127.0.0.1:5432/mcot_rental_db

# Production HTTPS (if you have SSL certificate)
SECURE_SSL_REDIRECT=true

# Email (Gmail SMTP with App Password)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
DEFAULT_FROM_EMAIL=MCOT Equipment <your-email@gmail.com>

# Site domain (for password reset links)
SITE_DOMAIN=mcotequipmentservices.mcot.net
```

### 1.3 Test Initial Migration

```bash
# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Test database connection
python3 manage.py dbshell
# If you get a psql prompt, it works. Type \q to exit.

# Run initial migration
python3 manage.py migrate

# Create superuser (for admin access)
python3 manage.py createsuperuser

# Test that app can start
python3 manage.py check --deploy
```

If all checks pass, you're ready to deploy.

---

## Step 2: Local Commit & Deploy

### 2.1 Commit Code Locally

```bash
# On your local machine
cd /path/to/MCOT_Rental_Platform

# Make sure everything is committed
git status

# Stage and commit (if you made changes)
git add .
git commit -m "feat: production deployment with PostgreSQL"

# Ensure you're on v3 branch
git checkout v3
git push origin v3
```

**⚠️ ERROR CHECK**: If git status shows uncommitted changes, the deploy script will abort. Commit them first!

### 2.2 Run Deploy Script

```bash
# Make script executable
chmod +x deploy_to_vps.sh

# Run deploy (script will handle git validation)
./deploy_to_vps.sh
```

**What the script does**:
1. ✅ Checks git working tree is clean
2. ✅ Pushes code to `v3` branch
3. ✅ SSH to VPS and validates DATABASE_URL
4. ✅ Runs `python3 manage.py check --deploy` (pre-flight)
5. ✅ Pulls latest code on VPS
6. ✅ **Backs up PostgreSQL database** before migration
7. ✅ Runs migrations
8. ✅ Collects static files
9. ✅ Restarts Gunicorn
10. ✅ Runs health check (post-deploy)

**Expected output**:
```
✅ Deployment complete!

📝 Verify deployment:
1. Check app logs: tail -f logs/error.log
2. Test website: https://mcotequipmentservices.mcot.net
3. Verify booking flow
```

---

## Step 3: Verify Deployment

### 3.1 Check Application Logs

```bash
# SSH to VPS
ssh -p 8022 ubuntu@43.173.251.244
cd ~/MCOT_Rental_Platform

# Watch error logs in real-time
tail -f logs/error.log
tail -f logs/app.log

# Or check Gunicorn systemd logs
sudo journalctl -u gunicorn -n 100 --no-pager
sudo journalctl -u gunicorn -f  # Real-time follow
```

### 3.2 Test Website

```bash
# Visit website
https://mcotequipmentservices.mcot.net

# Test key flows:
1. Home page loads
2. Can browse equipment catalog
3. Can add items to cart
4. Login/signup works
5. Can create booking (if customer)
6. Staff dashboard accessible (if staff)
```

### 3.3 Check Database

```bash
ssh ubuntu@43.173.251.244 -p 8022
cd ~/MCOT_Rental_Platform

# Activate venv
source venv/bin/activate

# Check database
python3 manage.py dbshell

# Inside psql prompt:
SELECT COUNT(*) FROM store_booking;  -- Count bookings
\dt                                   -- List all tables
\q                                    -- Exit
```

---

## Step 4: Troubleshooting

### Problem: "Database connection refused"

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check DATABASE_URL in .env
grep DATABASE_URL ~/MCOT_Rental_Platform/.env

# Test psql connection
psql -h 127.0.0.1 -U mcot_user -d mcot_rental_db -c "SELECT 1;"
```

### Problem: "Migrations failed"

```bash
# Check migration status
python3 manage.py showmigrations

# Rollback last migration (if needed)
python3 manage.py migrate store 0001

# Re-run migrations
python3 manage.py migrate
```

### Problem: "Gunicorn won't start"

```bash
# Check Gunicorn logs
sudo journalctl -u gunicorn -n 200 --no-pager

# Check if port 8000 is in use
ss -tlnp | grep 8000

# Manually test Django app
cd ~/MCOT_Rental_Platform
source venv/bin/activate
python3 manage.py check --deploy
python3 manage.py test apps.store.tests.BookingFlowTests.test_create_booking_success
```

### Problem: "Static files not loading"

```bash
# Recollect static files
python3 manage.py collectstatic --noinput --clear

# Verify static files exist
ls -la ~/MCOT_Rental_Platform/staticfiles/

# Reload Nginx
sudo systemctl reload nginx
```

### Problem: "Email not sending"

```bash
# Check email credentials
grep EMAIL ~/MCOT_Rental_Platform/.env

# Test email (local)
python3 manage.py shell
from django.core.mail import send_mail
send_mail('Test', 'Body', 'from@gmail.com', ['to@gmail.com'])
exit()
```

---

## Step 5: Rollback (If Something Breaks)

If deployment broke production, roll back to previous commit:

```bash
ssh ubuntu@43.173.251.244 -p 8022
cd ~/MCOT_Rental_Platform

# Check git log
git log --oneline -10

# Rollback to previous commit
git reset --hard <previous-commit-sha>

# Rerun deployment steps
source venv/bin/activate
python3 manage.py migrate
python3 manage.py collectstatic --noinput
sudo systemctl restart gunicorn

# Verify health
python3 manage.py check --deploy
```

Or use database backup if data was corrupted:

```bash
# List backups
ls -la backups/postgres/

# Restore from backup (carefull — this wipes current data)
CONFIRM_RESTORE=YES ./scripts/db_restore.sh backups/postgres/<filename>.sql.gz

# Then restart
sudo systemctl restart gunicorn
```

---

## Maintenance

### Daily Health Checks

```bash
# Quick status check
ssh -p 8022 ubuntu@43.173.251.244 "cd ~/MCOT_Rental_Platform && python3 manage.py check --deploy"

# Check for errors in logs
ssh -p 8022 ubuntu@43.173.251.244 "tail logs/error.log"

# Monitor disk space
ssh -p 8022 ubuntu@43.173.251.244 "df -h"
```

### Regular Backups

```bash
# Backup database (manual)
ssh -p 8022 ubuntu@43.173.251.244 "cd ~/MCOT_Rental_Platform && bash scripts/db_backup.sh"

# Check backup
ls -lah ~/backups/postgres/
```

### Update Dependencies

```bash
# Check for outdated packages
pip list --outdated

# Update specific package
pip install --upgrade django

# Test thoroughly in dev first, then deploy
```

---

## Architecture Overview

```
┌─────────────────────────────────┐
│   MCOT_Rental_Platform          │
│   (Django App)                  │
│   Port: 8000 (Gunicorn)         │
└───────────────┬─────────────────┘
                │
        ┌───────┴────────┐
        │                │
    ┌───▼────────┐  ┌──▼──────────┐
    │ PostgreSQL │  │  Nginx       │
    │ Port 5432  │  │  Port 80/443 │
    └─────────────  └──────────────┘
        
    Static Files: ~/staticfiles/
    Media Files: ~/media/
    Logs: ~/logs/
    Backups: ~/backups/postgres/
```

---

## Environment Variables Reference

| Variable | Example | Purpose |
|----------|---------|---------|
| `DEBUG` | `False` | Disable debug mode in production |
| `SECRET_KEY` | `abc123...` | Django secret key (random string) |
| `ALLOWED_HOSTS` | `mcot.net,www.mcot.net` | Domains allowed to access app |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `SECURE_SSL_REDIRECT` | `true` | Force HTTPS |
| `EMAIL_HOST_USER` | `email@gmail.com` | Gmail address |
| `EMAIL_HOST_PASSWORD` | `xxxx xxxx xxxx xxxx` | Gmail App Password (16 chars) |
| `SITE_DOMAIN` | `mcot.net` | Site domain for email links |

---

## Deploy Checklist (Before Each Release)

- [ ] All changes committed locally
- [ ] Branch is `v3` and pushed to origin
- [ ] `.env` file on VPS has correct DATABASE_URL
- [ ] Database backup taken
- [ ] `python3 manage.py check --deploy` passes locally
- [ ] Tests pass: `python3 manage.py test apps.store`
- [ ] Deploy script runs without errors
- [ ] Website loads and content is visible
- [ ] Login/signup works
- [ ] Booking flow works end-to-end
- [ ] Logs show no critical errors
- [ ] Email notifications still work

---

**Last Updated**: March 18, 2026  
**PostgreSQL Version**: 12+  
**Django Version**: 4.2.27  
**Python Version**: 3.9+
