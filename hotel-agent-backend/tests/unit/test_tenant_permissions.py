from uuid import uuid4

import pytest

from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.enums import (
    OrganizationRole,
    PropertyRole,
)
from app.modules.tenancy.service import (
    TenantAccessDeniedError,
    require_organization_owner,
    require_property_management_access,
)


def create_tenant_context(
    *,
    organization_role: OrganizationRole | None = None,
    property_role: PropertyRole | None = None,
    property_scope: bool = False,
) -> TenantContext:
    return TenantContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        property_id=uuid4() if property_scope else None,
        organization_role=organization_role,
        property_role=property_role,
    )


def test_organization_owner_permission_is_allowed() -> None:
    tenant_context = create_tenant_context(
        organization_role=OrganizationRole.ORGANIZATION_OWNER,
    )

    require_organization_owner(
        tenant_context,
    )


def test_organization_viewer_is_not_an_owner() -> None:
    tenant_context = create_tenant_context(
        organization_role=OrganizationRole.VIEWER,
    )

    with pytest.raises(
        TenantAccessDeniedError,
        match="Organization owner access is required",
    ):
        require_organization_owner(
            tenant_context,
        )


def test_property_manager_is_not_an_organization_owner() -> None:
    tenant_context = create_tenant_context(
        property_role=PropertyRole.PROPERTY_MANAGER,
        property_scope=True,
    )

    with pytest.raises(
        TenantAccessDeniedError,
        match="Organization owner access is required",
    ):
        require_organization_owner(
            tenant_context,
        )


def test_organization_owner_can_manage_property() -> None:
    tenant_context = create_tenant_context(
        organization_role=OrganizationRole.ORGANIZATION_OWNER,
        property_scope=True,
    )

    require_property_management_access(
        tenant_context,
    )


def test_property_manager_can_manage_property() -> None:
    tenant_context = create_tenant_context(
        property_role=PropertyRole.PROPERTY_MANAGER,
        property_scope=True,
    )

    require_property_management_access(
        tenant_context,
    )


def test_operations_manager_can_manage_property() -> None:
    tenant_context = create_tenant_context(
        property_role=PropertyRole.OPERATIONS_MANAGER,
        property_scope=True,
    )

    require_property_management_access(
        tenant_context,
    )


@pytest.mark.parametrize(
    "property_role",
    [
        PropertyRole.RESERVATION_MANAGER,
        PropertyRole.RESTAURANT_MANAGER,
        PropertyRole.EVENT_MANAGER,
        PropertyRole.SUPPORT_AGENT,
        PropertyRole.VIEWER,
    ],
)
def test_other_property_roles_cannot_manage_property(
    property_role: PropertyRole,
) -> None:
    tenant_context = create_tenant_context(
        property_role=property_role,
        property_scope=True,
    )

    with pytest.raises(
        TenantAccessDeniedError,
        match="Property management access is required",
    ):
        require_property_management_access(
            tenant_context,
        )
