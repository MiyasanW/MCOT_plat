#!/usr/bin/env bash
# รัน mark_overdue_and_notify (ตั้งใน cron ให้รันทุกวัน เช่น 00:05)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# ใช้ python จาก venv (เรียงตามที่โปรเจกต์มักใช้)
if [ -x "$ROOT/venv_mcot/bin/python" ]; then
    PY="$ROOT/venv_mcot/bin/python"
elif [ -x "$ROOT/mcot_env/bin/python" ]; then
    PY="$ROOT/mcot_env/bin/python"
elif [ -x "$ROOT/venv/bin/python" ]; then
    PY="$ROOT/venv/bin/python"
elif [ -x "$ROOT/venv_new/bin/python" ]; then
    PY="$ROOT/venv_new/bin/python"
else
    PY=python3
fi
exec "$PY" manage.py mark_overdue_and_notify
