# PR 2 Phase 2A — Apply and validate

Run these commands from `hotel-agent-backend`.

```powershell
git switch -c feature/pr2-tenancy
```

Copy the supplied `app/` and `migrations/env.py` files into the repository.

Verify model registration:

```powershell
python -c "from app.db.models import Base; print(sorted(Base.metadata.tables.keys()))"
```

Expected:

```text
['organization_memberships', 'organizations', 'properties', 'property_memberships']
```

Run static validation before contacting Supabase:

```powershell
python -m compileall app
python -m ruff format .
python -m ruff check .
python -m mypy app
```

Generate, but do not immediately apply, the migration:

```powershell
alembic revision --autogenerate -m "create tenancy tables"
```

Review the new file in `migrations/versions/`. It should create only:

- `organizations`
- `properties`
- `organization_memberships`
- `property_memberships`
- indexes and constraints belonging to those four tables

Important constraints to confirm:

- `uq_organizations_slug`
- `uq_properties_organization_id_code`
- `uq_properties_organization_id_id`
- `uq_organization_memberships_organization_id_user_id`
- `uq_property_memberships_property_id_user_id`
- `fk_property_memberships_property_organization`
- `ON DELETE CASCADE` on organization/property ownership constraints

Also verify that downgrade drops child tables first:

1. `property_memberships`
2. `organization_memberships`
3. `properties`
4. `organizations`

Then apply:

```powershell
alembic upgrade head
alembic current
```

Do not create the same tables manually in Supabase.

## Deliberate design decisions

- Membership `status` was included because the next tenancy-context phase requires inactive memberships to be rejected.
- User UUID columns are not yet foreign keys to `auth.users`. Supabase Auth is outside the application's SQLAlchemy metadata; authentication and RLS integration will be handled in the next phases.
- IANA timezone validity should be enforced in the API schema/service layer. The database currently prevents only blank values.
