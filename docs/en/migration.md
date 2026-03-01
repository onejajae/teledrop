# Migration Notes

Drop schema changed from legacy `content`/`contents` tables to `drops`.
The drop identifier column is now `drops.slug` (replacing legacy `drops.key`).

Before upgrading in production, back up your DB file:
```bash
cp share/database.db share/database.db.bak
```

Alembic files are provided under `migrations/`.
When running the official Docker image, container startup automatically runs:
```bash
alembic -c alembic.ini upgrade head
```

If you run teledrop outside the Docker entrypoint, run migration manually before app startup:
```bash
uv run alembic -c alembic.ini upgrade head
```
