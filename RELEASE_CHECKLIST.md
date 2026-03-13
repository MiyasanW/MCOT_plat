# Release Checklist (1 Page)

Use this checklist every time before deploying to production.

## 1) Scope Lock

1. Confirm branch and target commit.
2. Confirm what is included and what is not included.
3. Confirm rollback commit (last known good).

## 2) Pre-Release Validation

1. Run checks locally.

```bash
python3 manage.py check
python3 manage.py test apps.store.tests_cancellation apps.store.tests_state_transitions
```

2. Confirm no unintended files in git.

```bash
git status --short
```

3. Confirm env-sensitive values are not hardcoded.
4. Confirm migration impact (schema/data) is understood.

## 3) Production Readiness

1. Verify VPS service is healthy before deploy.

```bash
./scripts/health_check_vps.sh
```

2. Run database backup before deploy.

```bash
./scripts/db_backup.sh
```

3. Ensure enough disk space for backup and static files.

## 4) Deploy Steps

1. Pull latest code on VPS.
2. Install/update dependencies.
3. Run migrations.
4. Collect static files.
5. Restart application service.

## 5) Post-Deploy Smoke Test

1. Run smoke test against production domain.

```bash
BASE_URL=https://mcotequipmentservices.mcot.net ./scripts/smoke_test.sh
```

2. Verify key user flow quickly:
1. login
2. catalog
3. my bookings
4. booking detail (staff/customer)

## 6) Rollback Plan (If Needed)

1. Checkout rollback commit.
2. Re-run migrate/collectstatic.
3. Restart service.
4. Re-run smoke test.

## 7) Sign-Off

1. Record deployed commit SHA.
2. Record deploy time and operator.
3. Record result (pass/fail) and notes.
