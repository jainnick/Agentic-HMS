from __future__ import annotations

from app.modules.assistant.llm import (
    build_assistant_tool_definitions,
    build_knowledge_search_tool_definition,
    build_room_availability_tool_definition,
)
from app.modules.property_tools import (
    PropertyToolName,
)


def test_knowledge_tool_definition_uses_valid_provider_name() -> None:
    definition = build_knowledge_search_tool_definition()

    function_definition = definition["function"]

    assert function_definition["name"] == "knowledge_search"

    parameters = function_definition["parameters"]

    assert "query" in parameters["properties"]

    assert "organization_id" not in parameters["properties"]

    assert "property_id" not in parameters["properties"]


def test_room_availability_definition_has_safe_arguments() -> None:
    definition = build_room_availability_tool_definition()

    function_definition = definition["function"]

    assert function_definition["name"] == "room_availability"

    parameters = function_definition["parameters"]

    properties = parameters["properties"]

    assert "check_in" in properties
    assert "check_out" in properties
    assert "adults" in properties
    assert "children" in properties
    assert "rooms" in properties
    assert "room_type" in properties

    assert "organization_id" not in properties

    assert "property_id" not in properties


def test_enabled_tools_are_exposed() -> None:
    definitions = build_assistant_tool_definitions(
        {
            PropertyToolName.KNOWLEDGE_SEARCH,
            PropertyToolName.ROOM_AVAILABILITY,
        }
    )

    names = {definition["function"]["name"] for definition in definitions}

    assert names == {
        "knowledge_search",
        "room_availability",
    }


def test_disabled_availability_is_not_exposed() -> None:
    definitions = build_assistant_tool_definitions(
        {
            PropertyToolName.KNOWLEDGE_SEARCH,
        }
    )

    names = {definition["function"]["name"] for definition in definitions}

    assert names == {
        "knowledge_search",
    }


def test_room_booking_is_exposed_when_enabled() -> None:
    definitions = build_assistant_tool_definitions(
        {
            PropertyToolName.KNOWLEDGE_SEARCH,
            PropertyToolName.ROOM_AVAILABILITY,
            PropertyToolName.ROOM_BOOKING,
        }
    )

    names = {
        definition["function"]["name"]
        for definition in definitions
    }

    assert names == {
        "knowledge_search",
        "room_availability",
        "room_booking",
    }
