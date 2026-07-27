from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.schemas import CurrentUser
from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.enums import (
    LifecycleStatus,
    OrganizationRole,
    PropertyRole,
)
from app.modules.tenancy.models import (
    Organization,
    OrganizationMembership,
    Property,
    PropertyMembership,
)


class TenantContextResolutionError(Exception):
    """Base error for tenant-context resolution failures."""


class TenantResourceNotFoundError(TenantContextResolutionError):
    """Raised when an active organization or property cannot be found."""


class TenantAccessDeniedError(TenantContextResolutionError):
    """Raised when the user has no active membership for the requested scope."""


async def resolve_tenant_context(
    session: AsyncSession,
    *,
    current_user: CurrentUser,
    organization_id: UUID,
    property_id: UUID | None = None,
) -> TenantContext:
    """
    Resolve a verified organization/property context for an authenticated user.

    The client may request an organization and property, but this function
    verifies that:

    - the organization exists and is active;
    - the property exists, is active, and belongs to the organization;
    - the user has an active organization or property membership.

    Organization-scope requests require an organization membership.
    Property-scope requests allow either an organization membership or a
    property-specific membership.
    """

    organization_statement = (
        select(
            Organization.id,
            OrganizationMembership.role,
        )
        .outerjoin(
            OrganizationMembership,
            and_(
                OrganizationMembership.organization_id == Organization.id,
                OrganizationMembership.user_id == current_user.id,
                OrganizationMembership.status == LifecycleStatus.ACTIVE,
            ),
        )
        .where(
            Organization.id == organization_id,
            Organization.status == LifecycleStatus.ACTIVE,
        )
    )

    organization_row = (
        await session.execute(
            organization_statement,
        )
    ).one_or_none()

    if organization_row is None:
        raise TenantResourceNotFoundError(
            "The requested organization was not found or is inactive.",
        )

    organization_role = organization_row[1]

    if property_id is None:
        if organization_role is None:
            raise TenantAccessDeniedError(
                "The user does not have access to this organization.",
            )

        return TenantContext(
            user_id=current_user.id,
            organization_id=organization_id,
            property_id=None,
            organization_role=organization_role,
            property_role=None,
        )

    property_statement = (
        select(
            Property.id,
            PropertyMembership.role,
        )
        .outerjoin(
            PropertyMembership,
            and_(
                PropertyMembership.organization_id == Property.organization_id,
                PropertyMembership.property_id == Property.id,
                PropertyMembership.user_id == current_user.id,
                PropertyMembership.status == LifecycleStatus.ACTIVE,
            ),
        )
        .where(
            Property.id == property_id,
            Property.organization_id == organization_id,
            Property.status == LifecycleStatus.ACTIVE,
        )
    )

    property_row = (
        await session.execute(
            property_statement,
        )
    ).one_or_none()

    if property_row is None:
        raise TenantResourceNotFoundError(
            "The requested property was not found, is inactive, "
            "or does not belong to the organization.",
        )

    property_role = property_row[1]

    if organization_role is None and property_role is None:
        raise TenantAccessDeniedError(
            "The user does not have access to this property.",
        )

    return TenantContext(
        user_id=current_user.id,
        organization_id=organization_id,
        property_id=property_id,
        organization_role=organization_role,
        property_role=property_role,
    )


def require_organization_owner(
    tenant_context: TenantContext,
) -> None:
    """
    Require organization-owner access.

    This is used for organization-wide operations such as creating properties,
    managing organization settings, and inviting organization administrators.
    """

    if tenant_context.organization_role != OrganizationRole.ORGANIZATION_OWNER:
        raise TenantAccessDeniedError(
            "Organization owner access is required.",
        )


def require_property_management_access(
    tenant_context: TenantContext,
) -> None:
    """
    Require permission to manage the selected hotel property.

    Organization owners may manage every property in their organization.
    Property and operations managers may manage their assigned property.
    """

    if tenant_context.organization_role == OrganizationRole.ORGANIZATION_OWNER:
        return

    allowed_property_roles = {
        PropertyRole.PROPERTY_MANAGER,
        PropertyRole.OPERATIONS_MANAGER,
    }

    if tenant_context.property_role not in allowed_property_roles:
        raise TenantAccessDeniedError(
            "Property management access is required.",
        )
