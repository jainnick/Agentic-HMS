from __future__ import annotations

from typing import Any

import pytest

from app.modules.knowledge import embeddings


class FakeEncodedRows:
    """
    Test replacement for the NumPy array returned by Sentence Transformers.
    """

    def __init__(
        self,
        rows: list[list[float]],
    ) -> None:
        self.rows = rows

    def tolist(
        self,
    ) -> list[list[float]]:
        return self.rows


class FakeEmbeddingModel:
    """
    Test embedding model.

    It returns predictable vectors without downloading or running a real
    machine-learning model.
    """

    def __init__(
        self,
        *,
        dimension: int = 384,
    ) -> None:
        self.dimension = dimension
        self.received_texts: list[str] = []

    def encode(
        self,
        sentences: list[str],
        **_: Any,
    ) -> FakeEncodedRows:
        self.received_texts = sentences

        rows = [
            [
                1.0,
                *([0.0] * (self.dimension - 1)),
            ]
            for _ in sentences
        ]

        return FakeEncodedRows(
            rows,
        )


def test_embed_texts_returns_one_vector_per_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeEmbeddingModel()

    monkeypatch.setattr(
        embeddings,
        "get_embedding_model",
        lambda: fake_model,
    )

    vectors = embeddings.embed_texts(
        [
            "Pets are allowed.",
            "Checkout is at 11 AM.",
        ]
    )

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384


def test_embed_texts_normalizes_whitespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeEmbeddingModel()

    monkeypatch.setattr(
        embeddings,
        "get_embedding_model",
        lambda: fake_model,
    )

    embeddings.embed_texts(
        [
            "Pets   are\nallowed.",
        ]
    )

    assert fake_model.received_texts == [
        "Pets are allowed.",
    ]


def test_embed_texts_rejects_empty_list() -> None:
    with pytest.raises(
        embeddings.EmbeddingInputError,
        match="At least one text",
    ):
        embeddings.embed_texts([])


def test_embed_texts_rejects_blank_text() -> None:
    with pytest.raises(
        embeddings.EmbeddingInputError,
        match="index 0 is empty",
    ):
        embeddings.embed_texts(
            [
                "   \n\t   ",
            ]
        )


def test_embed_texts_rejects_invalid_batch_size() -> None:
    with pytest.raises(
        embeddings.EmbeddingInputError,
        match="batch size",
    ):
        embeddings.embed_texts(
            [
                "Hotel policy text.",
            ],
            batch_size=0,
        )


def test_embed_texts_rejects_wrong_dimension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeEmbeddingModel(
        dimension=10,
    )

    monkeypatch.setattr(
        embeddings,
        "get_embedding_model",
        lambda: fake_model,
    )

    with pytest.raises(
        embeddings.EmbeddingDimensionError,
        match="dimension 10",
    ):
        embeddings.embed_texts(
            [
                "Hotel policy text.",
            ]
        )


def test_embed_query_returns_one_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeEmbeddingModel()

    monkeypatch.setattr(
        embeddings,
        "get_embedding_model",
        lambda: fake_model,
    )

    vector = embeddings.embed_query("Can I bring my dog?")

    assert len(vector) == 384


@pytest.mark.asyncio
async def test_embed_texts_async_returns_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeEmbeddingModel()

    monkeypatch.setattr(
        embeddings,
        "get_embedding_model",
        lambda: fake_model,
    )

    vectors = await embeddings.embed_texts_async(
        [
            "Breakfast starts at 7 AM.",
        ]
    )

    assert len(vectors) == 1
    assert len(vectors[0]) == 384
