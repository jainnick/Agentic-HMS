from enum import StrEnum


class LifecycleStatus(StrEnum):
    """Lifecycle state for organizations, properties, and memberships."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class OrganizationRole(StrEnum):
    """Roles granted at organization scope."""

    ORGANIZATION_OWNER = "organization_owner"
    VIEWER = "viewer"


class PropertyRole(StrEnum):
    """Roles granted at property scope."""

    PROPERTY_MANAGER = "property_manager"
    RESERVATION_MANAGER = "reservation_manager"
    RESTAURANT_MANAGER = "restaurant_manager"
    EVENT_MANAGER = "event_manager"
    OPERATIONS_MANAGER = "operations_manager"
    SUPPORT_AGENT = "support_agent"
    VIEWER = "viewer"
