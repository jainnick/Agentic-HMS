from __future__ import annotations

from enum import StrEnum
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class OnboardingStep(StrEnum):
    CREATE_ORGANIZATION = "create_organization"
    CREATE_PROPERTY = "create_property"
    COMPLETED = "completed"


class OnboardingStatusResponse(BaseModel):
    """Current onboarding state for the authenticated platform user."""

    has_organization: bool
    has_property: bool
    next_step: OnboardingStep

    organization_id: UUID | None = None
    property_id: UUID | None = None


class OrganizationCreateRequest(BaseModel):
    """Details required to create the user's first hotel organization."""

    name: str = Field(
        min_length=2,
        max_length=255,
    )

    @field_validator(
        "name",
        mode="before",
    )
    @classmethod
    def normalize_name(
        cls,
        value: object,
    ) -> str:
        """
        Trim external whitespace and collapse repeated internal whitespace.

        This validator runs before Pydantic's length checks so values such as
        '  Demo   Hotels  ' are validated after normalization.
        """

        if not isinstance(value, str):
            raise ValueError(
                "Organization name must be a string.",
            )

        normalized = " ".join(
            value.strip().split(),
        )

        if not normalized:
            raise ValueError(
                "Organization name cannot be blank.",
            )

        return normalized


class OrganizationCreateResponse(BaseModel):
    """Organization created during initial onboarding."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    name: str
    slug: str


class PropertyCreateRequest(BaseModel):
    """Details required to create the user's first hotel property."""

    name: str = Field(
        min_length=2,
        max_length=255,
    )
    code: str = Field(
        min_length=2,
        max_length=64,
    )
    timezone: str = Field(
        min_length=1,
        max_length=64,
    )
    currency: str = Field(
        min_length=3,
        max_length=3,
    )

    @field_validator(
        "name",
        mode="before",
    )
    @classmethod
    def normalize_property_name(
        cls,
        value: object,
    ) -> str:
        """Normalize the property name before validating its length."""

        if not isinstance(value, str):
            raise ValueError(
                "Property name must be a string.",
            )

        normalized = " ".join(
            value.strip().split(),
        )

        if not normalized:
            raise ValueError(
                "Property name cannot be blank.",
            )

        return normalized

    @field_validator(
        "code",
        mode="before",
    )
    @classmethod
    def normalize_property_code(
        cls,
        value: object,
    ) -> str:
        """Trim and uppercase the property code before length validation."""

        if not isinstance(value, str):
            raise ValueError(
                "Property code must be a string.",
            )

        normalized = value.strip().upper()

        if not normalized:
            raise ValueError(
                "Property code cannot be blank.",
            )

        return normalized

    @field_validator(
        "currency",
        mode="before",
    )
    @classmethod
    def normalize_currency(
        cls,
        value: object,
    ) -> str:
        """
        Trim and uppercase the ISO-style currency code before validation.

        The database currently requires three uppercase characters. A complete
        ISO 4217 catalogue validation can be added later if actually needed.
        """

        if not isinstance(value, str):
            raise ValueError(
                "Currency must be a string.",
            )

        normalized = value.strip().upper()

        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError(
                "Currency must contain exactly three letters.",
            )

        return normalized

    @field_validator(
        "timezone",
        mode="before",
    )
    @classmethod
    def validate_timezone(
        cls,
        value: object,
    ) -> str:
        """Normalize and validate an IANA timezone name."""

        if not isinstance(value, str):
            raise ValueError(
                "Timezone must be a string.",
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Timezone cannot be blank.",
            )

        try:
            ZoneInfo(normalized)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                "Timezone must be a valid IANA timezone.",
            ) from exc

        return normalized


class PropertyCreateResponse(BaseModel):
    """Property created during initial onboarding."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    organization_id: UUID
    name: str
    code: str
    timezone: str
    currency: str