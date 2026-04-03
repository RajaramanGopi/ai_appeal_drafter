"""Tokenizer chunking and batch embedding helpers."""
from __future__ import annotations

from knowledge_base import ingest


class _FakeTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False):  # noqa: ARG002
        return [int(token) for token in text.split() if token.strip()]

    def decode(self, token_ids, skip_special_tokens: bool = True):  # noqa: ARG002
        return " ".join(str(token) for token in token_ids)


class _FakeModel:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, batch, batch_size: int, show_progress_bar: bool = False):  # noqa: ARG002
        self.calls.append(list(batch))

        class _Vectors:
            def __init__(self, n: int) -> None:
                self.n = n

            def tolist(self):
                return [[0.0, 1.0] for _ in range(self.n)]

        return _Vectors(len(batch))


def test_token_chunking_respects_overlap():
    tokenizer = _FakeTokenizer()
    text = "1 2 3 4 5 6 7 8 9"
    chunks = ingest._chunk_text_with_tokenizer(text, tokenizer, chunk_token_size=4, token_overlap=1)
    assert chunks == ["1 2 3 4", "4 5 6 7", "7 8 9"]


def test_batch_embedding_processes_multiple_batches():
    model = _FakeModel()
    texts = ["a", "b", "c", "d", "e"]
    vectors = ingest._encode_embeddings_in_batches(model, texts, batch_size=2)
    assert len(model.calls) == 3
    assert model.calls == [["a", "b"], ["c", "d"], ["e"]]
    assert len(vectors) == 5
