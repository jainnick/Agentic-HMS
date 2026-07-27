from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.modules.tenancy.enums import (
    OrganizationRole,
    PropertyRole,
)


class TenantContext(BaseModel):
    """
    Verified organization and property scope for an authenticated request.

    This object must be created only after the backend has checked:
    - the organization exists and is active;
    - the property exists and belongs to the organization;
    - the authenticated user has an active organization or property membership.
    """

    model_config = ConfigDict(
        frozen=True,
    )

    user_id: UUID
    organization_id: UUID
    property_id: UUID | None = None

    organization_role: OrganizationRole | None = None
    property_role: PropertyRole | None = None

    @model_validator(mode="after")
    def validate_tenant_context(self) -> TenantContext:
        """
        Prevent invalid tenant-context combinations.

        A property role cannot exist unless a property is selected, and at
        least one verified membership role must be present.
        """

        if self.property_id is None and self.property_role is not None:
            raise ValueError(
                "property_role cannot be provided without property_id.",
            )

        if self.organization_role is None and self.property_role is None:
            raise ValueError(
                "Tenant context requires at least one verified membership role.",
            )

        return self

    @property
    def is_organization_scope(self) -> bool:
        """Return True when the request operates only at organization level."""

        return self.property_id is None

    @property
    def is_property_scope(self) -> bool:
        """Return True when the request operates on a specific hotel property."""

        return self.property_id is not None

    @property
    def role_names(self) -> frozenset[str]:
        """Return all verified organization and property role names."""

        roles: set[str] = set()

        if self.organization_role is not None:
            roles.add(self.organization_role.value)

        if self.property_role is not None:
            roles.add(self.property_role.value)

        return frozenset(roles)
