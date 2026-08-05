from __future__ import annotations

from app.modules.assistant.llm import (
    build_knowledge_search_tool_definition,
)


def test_knowledge_tool_definition_uses_valid_provider_name() -> None:
    definition = build_knowledge_search_tool_definition()

    function_definition = definition["function"]

    assert function_definition["name"] == ("knowledge_search")

    parameters = function_definition["parameters"]

    assert "query" in parameters["properties"]
    assert "organization_id" not in (parameters["properties"])
    assert "property_id" not in (parameters["properties"])
