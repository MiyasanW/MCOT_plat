# MCOT Equipment Service

![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/django-4.2-0C4B33?logo=django&logoColor=white)
![Branch](https://img.shields.io/badge/deploy-v3-orange)
![Status](https://img.shields.io/badge/status-active-success)

Django-based rental platform for professional production equipment, studios, packages, and supporting services.

## Highlights

- Equipment catalog and availability flow
- Studio booking and package booking
- Quotation and payment confirmation flow
- Staff dashboard and booking summary tools
- Google login via django-allauth
- Thai-first UX and localized validation/messages

## Tech Stack

- Python 3.9+
- Django 4.2
- PostgreSQL (production)
- SQLite (local fallback)
- django-allauth, django-filter, django-import-export
- xhtml2pdf (quotation/pdf generation)

## Project Structure

```text
.
├── apps/store/                # Main business app (models, views, services)
├── config/                    # Django settings, urls, wsgi/asgi
├── templates/                 # Frontend templates
├── static/                    # Project static assets
├── media/                     # Uploaded files
├── requirements.txt
├── manage.py
└── deploy_to_vps.sh
```

## Quick Start (Local)

1. Clone project

```bash
git clone https://github.com/MiyasanW/MCOT_plat.git
cd MCOT_Rental_Platform
```

2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Configure environment

```bash
cp .env.example .env
```

Edit .env values for your machine.

5. Run migrations

```bash
python3 manage.py migrate
```

6. Run server

```bash
python3 manage.py runserver
```

Open http://127.0.0.1:8000

## Environment Variables

Minimum production variables:

- DEBUG
- SECRET_KEY
- ALLOWED_HOSTS
- DATABASE_URL
- EMAIL_HOST
- EMAIL_PORT
- EMAIL_USE_TLS
- EMAIL_HOST_USER
- EMAIL_HOST_PASSWORD
- DEFAULT_FROM_EMAIL
- SITE_DOMAIN

See .env.example for a complete template.

## Validation Commands

```bash
python3 manage.py check
python3 manage.py test
```

## Core Routes and API

Main web routes:

- `/` home
- `/catalog/` equipment catalog
- `/cart/`, `/cart/dates/`, `/cart/review/` booking flow
- `/my-bookings/` customer bookings dashboard
- `/staff/dashboard/` staff dashboard

Key API endpoints:

- `GET /api/check-availability/`
- `GET /api/check-cart/`
- `GET /api/check-promo/`
- `POST /api/booking/create/`
- `POST /api/booking/<booking_id>/cancel/`
- `GET /api/calendar/events/`
- `GET /api/notifications/`
- `POST /api/notifications/read/`
- `POST /api/booking/<booking_id>/upload-slip/`
- `GET /api/booking/<booking_id>/quotation/`

## Deployment (VPS, Branch v3)

Current production rollout branch is v3.

### One-time SSH key setup

```bash
bash setup_ssh_key.sh
```

### Quick deploy script

```bash
bash deploy_to_vps.sh
```

The script pushes/pulls branch `v3`, runs migrations, collects static files, and restarts `gunicorn`.

### Deploy flow

1. Push code to v3

```bash
git push origin v3
```

2. SSH to VPS and deploy

```bash
ssh -i ~/.ssh/id_ed25519_mcot -p 8022 ubuntu@43.173.251.244
cd ~/MCOT_Rental_Platform  # or ~/mcot
source venv/bin/activate   # or source env/bin/activate

git fetch origin
git checkout v3
git pull --ff-only origin v3
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl is-active gunicorn
```

If status is active, deployment is healthy.

## Screenshots

Add project screenshots in your GitHub repository (recommended folder: `docs/screenshots/`) and reference them like this:

```md
![Landing Page](docs/screenshots/landing.png)
![Catalog Page](docs/screenshots/catalog.png)
![Booking Review](docs/screenshots/booking-review.png)
![Staff Dashboard](docs/screenshots/staff-dashboard.png)
```

## Notes

- Keep .env and local database files out of public commits.

## License

Internal project for MCOT Equipment Service.
