from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenancy.context import TenantContext


class AssistantToolContextError(Exception):
    """Raised when a tool does not have the trusted context it requires."""


@dataclass(frozen=True, slots=True)
class AssistantToolContext:
    """
    Trusted backend context supplied to assistant tools.

    Tool-call arguments come from the LLM and therefore cannot be trusted.
    Tenant identifiers come from this backend-created context instead.
    """

    session: AsyncSession
    organization_id: UUID
    property_id: UUID

    @classmethod
    def from_tenant_context(
        cls,
        *,
        session: AsyncSession,
        tenant_context: TenantContext,
    ) -> AssistantToolContext:
        """
        Create an assistant context from a verified authenticated tenant.

        This is useful for administrative and authenticated assistant routes.
        The future public widget can create this context after resolving its
        own trusted widget/property configuration.
        """

        property_id = tenant_context.property_id

        if property_id is None:
            raise AssistantToolContextError(
                "A property must be selected before assistant tools can run."
            )

        return cls(
            session=session,
            organization_id=tenant_context.organization_id,
            property_id=property_id,
        )
