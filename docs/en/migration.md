# Migration Notes

This version intentionally breaks compatibility with older database schemas. The app no longer ships Alembic migrations and does not attempt to convert existing `content`/`contents` tables or older `drops`, `auth_sessions`, and `auth_api_keys` layouts.

Before upgrading in production, back up your database file:
```bash
cp share/database.db share/database.db.bak
```

Then remove the old database file before starting this version:
```bash
rm share/database.db
```

On startup, teledrop creates the current schema automatically and bootstraps the first web user from `WEB_USERNAME` and `WEB_PASSWORD`. Existing uploaded files under `share/` are not reattached to the new database automatically.
