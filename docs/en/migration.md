# Migration Notes

Drop schema changed from legacy `content`/`contents` tables to `drops`.
The drop identifier column is now `drops.slug` (replacing legacy `drops.key`).

Before upgrading in production, back up your DB file:
```bash
cp share/database.db share/database.db.bak
```

Alembic files are provided under `migrations/`. Runtime startup also performs schema compatibility migration (`drops.key` -> `drops.slug`) and legacy `content`/`contents` -> `drops` migration if needed.
If you want to run Alembic manually, install it in your environment first (`pip install alembic`).
