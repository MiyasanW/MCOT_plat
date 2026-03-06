# 🤖 AI Context: MCOT Rental Platform

**Welcome, next AI assistant!** Please read this document first to quickly understand the project context, stack, and recent updates.

## 📌 Project Overview

- **Name**: MCOT Rental Platform
- **Purpose**: A comprehensive rental system for MCOT (บมจ. อสมท) managing production equipment, studios, packages, and OB services. It handles the entire flow: cart selection, checking availability, booking, quotation generation, payment confirmation, and equipment handover.
- **Git Branch**: Currently working and deploying from the `v2` branch.

## 🛠 Tech Stack

- **Backend**: Python 3.9+ / Django 4.2.27
- **Database**:
  - **Production (VPS)**: PostgreSQL 16
  - **Local Development**: SQLite (`db_mock.sqlite3`)
  - Configured seamlessly using `dj-database-url` in `config/settings.py`.
- **Authentication**: `django-allauth` configured for Google OAuth2 Login.
- **Frontend**: HTML Templates, Tailwind CSS (via CDN), Alpine.js (for interactivity like dropdowns).
- **PDF Generation**: `xhtml2pdf` (used for Generating Quotations and Equipment Sheets).
- **Other Key Packages**: `django-simple-history`, `django-import-export`, `django-filter`, `crispy-bootstrap5`.

## 🚀 Recent Major Updates (March 2026)

1. **Quotation Flow & Email System**:
   - Added functionality for Staff to generate Quoation PDFs (`ใบเสนอราคา`) and email them directly to customers as attachments.
   - The mail backend defaults to Gmail SMTP (configured via environment variables).
2. **PostgreSQL Migration**:
   - Moved away from SQLite for production. The VPS now fully runs on PostgreSQL.
   - Local DB dumped to `data.json` and loaded into the VPS database successfully (2000+ objects).
3. **Navbar Redesign**:
   - Removed deep dropdowns in favor of a "Flat Pill" navigation design.
   - Now features a prominent gradient "ALL EQUIPMENT" button alongside color-coded sub-categories (Equipment, Packages, OB/Services, Studios) with FontAwesome icons.
4. **Smart Notification Polling**:
   - Integrated the Page Visibility API in `templates/base.html` to pause background notification polling when the browser tab is hidden, drastically reducing unnecessary API calls.

## 🖥 Deployment & Server Info

- **VPS IP**: `43.173.251.244`
- **SSH Port**: `8022`
- **User**: `ubuntu`
- **SSH Key**: `~/.ssh/id_ed25519_mcot` (Set up for passwordless login)
- **Path on VPS**: `/home/ubuntu/MCOT_Rental_Platform`
- **Virtual Env on VPS**: `venv_new`
- **Running State**: Currently running in the background via `nohup python3 manage.py runserver 0.0.0.0:8000 &`.
- **Deployment Script**: `deploy_to_vps.sh` (Pushes local `v2` branch to GitHub, SSHs into VPS, pulls `v2` branch, runs migrations).

## 📂 Key Files & Logic

- **`config/settings.py`**: Contains `dj-database-url` config, Allauth settings, and Email SMTP logic.
- **`apps/store/services/notification_service.py`**: Handles sending emails with PDF attachments.
- **`apps/store/views/staff.py`**: Contains the logic for the Staff Dashboard, PDF generation (`send_quotation` action), and state management.
- **`templates/base.html`**: Core layout, containing the new Flat Pill Navbar and smart notification polling script.
- **`templates/booking/pdf/`**: Contains the HTML templates used by `xhtml2pdf` to generate documents (`quotation.html`, `equipment_sheet.html`).

---

**Next Steps for AI**: Start by reviewing the user's new request. If debugging the database, test locally against `db_mock.sqlite3` first before SSHing into the VPS to interact with PostgreSQL.
