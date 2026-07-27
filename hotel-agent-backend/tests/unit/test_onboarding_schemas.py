import pytest
from pydantic import ValidationError

from app.modules.onboarding.schemas import (
    OrganizationCreateRequest,
    PropertyCreateRequest,
)


def test_organization_name_is_normalized() -> None:
    payload = OrganizationCreateRequest(
        name="   Demo    Hotels   Private   Limited   ",
    )

    assert payload.name == "Demo Hotels Private Limited"


def test_property_fields_are_normalized() -> None:
    payload = PropertyCreateRequest(
        name="   Demo    Hotel   Delhi   ",
        code="  del-01  ",
        timezone="Asia/Kolkata",
        currency=" inr ",
    )

    assert payload.name == "Demo Hotel Delhi"
    assert payload.code == "DEL-01"
    assert payload.timezone == "Asia/Kolkata"
    assert payload.currency == "INR"


@pytest.mark.parametrize(
    "timezone",
    [
        "",
        "Invalid/Timezone",
        "India/NewDelhi",
        "Mars/Olympus",
    ],
)
def test_invalid_timezone_is_rejected(
    timezone: str,
) -> None:
    with pytest.raises(ValidationError):
        PropertyCreateRequest(
            name="Demo Hotel",
            code="DEL01",
            timezone=timezone,
            currency="INR",
        )


@pytest.mark.parametrize(
    "currency",
    [
        "IN",
        "INRR",
        "1NR",
        "₹₹₹",
        "",
    ],
)
def test_invalid_currency_is_rejected(
    currency: str,
) -> None:
    with pytest.raises(ValidationError):
        PropertyCreateRequest(
            name="Demo Hotel",
            code="DEL01",
            timezone="Asia/Kolkata",
            currency=currency,
        )


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        "A",
    ],
)
def test_invalid_organization_name_is_rejected(
    name: str,
) -> None:
    with pytest.raises(ValidationError):
        OrganizationCreateRequest(
            name=name,
        )


@pytest.mark.parametrize(
    "code",
    [
        "",
        " ",
        "A",
    ],
)
def test_invalid_property_code_is_rejected(
    code: str,
) -> None:
    with pytest.raises(ValidationError):
        PropertyCreateRequest(
            name="Demo Hotel",
            code=code,
            timezone="Asia/Kolkata",
            currency="INR",
        )
