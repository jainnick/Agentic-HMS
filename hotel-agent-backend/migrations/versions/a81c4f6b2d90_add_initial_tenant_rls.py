"""add initial tenant rls

Revision ID: a81c4f6b2d90
Revises: f97cc2fbe621
Create Date: 2026-07-27

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a81c4f6b2d90"
down_revision: str | Sequence[str] | None = "f97cc2fbe621"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Enable tenant-aware read isolation for Supabase authenticated users.

    Direct writes through Supabase REST are intentionally not allowed yet.
    All onboarding and administrative writes continue through the FastAPI
    backend.
    """

    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS private
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION private.can_access_organization(
            target_organization_id uuid
        )
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT
                EXISTS (
                    SELECT 1
                    FROM public.organization_memberships AS membership
                    WHERE membership.organization_id = target_organization_id
                      AND membership.user_id = (SELECT auth.uid())
                      AND membership.status = 'active'
                )
                OR EXISTS (
                    SELECT 1
                    FROM public.property_memberships AS membership
                    WHERE membership.organization_id = target_organization_id
                      AND membership.user_id = (SELECT auth.uid())
                      AND membership.status = 'active'
                );
        $$
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION private.can_access_property(
            target_organization_id uuid,
            target_property_id uuid
        )
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT
                EXISTS (
                    SELECT 1
                    FROM public.organization_memberships AS membership
                    WHERE membership.organization_id = target_organization_id
                      AND membership.user_id = (SELECT auth.uid())
                      AND membership.status = 'active'
                )
                OR EXISTS (
                    SELECT 1
                    FROM public.property_memberships AS membership
                    WHERE membership.organization_id = target_organization_id
                      AND membership.property_id = target_property_id
                      AND membership.user_id = (SELECT auth.uid())
                      AND membership.status = 'active'
                );
        $$
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION private.is_organization_owner(
            target_organization_id uuid
        )
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT EXISTS (
                SELECT 1
                FROM public.organization_memberships AS membership
                WHERE membership.organization_id = target_organization_id
                  AND membership.user_id = (SELECT auth.uid())
                  AND membership.role = 'organization_owner'
                  AND membership.status = 'active'
            );
        $$
        """
    )

    op.execute(
        """
        REVOKE ALL
        ON FUNCTION private.can_access_organization(uuid)
        FROM PUBLIC
        """
    )

    op.execute(
        """
        REVOKE ALL
        ON FUNCTION private.can_access_property(uuid, uuid)
        FROM PUBLIC
        """
    )

    op.execute(
        """
        REVOKE ALL
        ON FUNCTION private.is_organization_owner(uuid)
        FROM PUBLIC
        """
    )

    op.execute(
        """
        GRANT USAGE ON SCHEMA private TO authenticated
        """
    )

    op.execute(
        """
        GRANT EXECUTE
        ON FUNCTION private.can_access_organization(uuid)
        TO authenticated
        """
    )

    op.execute(
        """
        GRANT EXECUTE
        ON FUNCTION private.can_access_property(uuid, uuid)
        TO authenticated
        """
    )

    op.execute(
        """
        GRANT EXECUTE
        ON FUNCTION private.is_organization_owner(uuid)
        TO authenticated
        """
    )

    op.execute(
        """
        GRANT SELECT ON
            public.organizations,
            public.properties,
            public.organization_memberships,
            public.property_memberships
        TO authenticated
        """
    )

    op.execute("ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.properties ENABLE ROW LEVEL SECURITY")
    op.execute(
        "ALTER TABLE public.organization_memberships ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE public.property_memberships ENABLE ROW LEVEL SECURITY"
    )

    op.execute(
        """
        CREATE POLICY organizations_select_for_members
        ON public.organizations
        FOR SELECT
        TO authenticated
        USING (
            private.can_access_organization(id)
        )
        """
    )

    op.execute(
        """
        CREATE POLICY properties_select_for_members
        ON public.properties
        FOR SELECT
        TO authenticated
        USING (
            private.can_access_property(
                organization_id,
                id
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY organization_memberships_select
        ON public.organization_memberships
        FOR SELECT
        TO authenticated
        USING (
            user_id = (SELECT auth.uid())
            OR private.is_organization_owner(organization_id)
        )
        """
    )

    op.execute(
        """
        CREATE POLICY property_memberships_select
        ON public.property_memberships
        FOR SELECT
        TO authenticated
        USING (
            user_id = (SELECT auth.uid())
            OR private.is_organization_owner(organization_id)
        )
        """
    )


def downgrade() -> None:
    """Remove the initial tenant RLS configuration."""

    op.execute(
        """
        DROP POLICY IF EXISTS property_memberships_select
        ON public.property_memberships
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS organization_memberships_select
        ON public.organization_memberships
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS properties_select_for_members
        ON public.properties
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS organizations_select_for_members
        ON public.organizations
        """
    )

    op.execute(
        "ALTER TABLE public.property_memberships DISABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE public.organization_memberships DISABLE ROW LEVEL SECURITY"
    )
    op.execute("ALTER TABLE public.properties DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.organizations DISABLE ROW LEVEL SECURITY")

    op.execute(
        """
        REVOKE SELECT ON
            public.organizations,
            public.properties,
            public.organization_memberships,
            public.property_memberships
        FROM authenticated
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS private.is_organization_owner(uuid)
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS private.can_access_property(uuid, uuid)
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS private.can_access_organization(uuid)
        """
    )