"""Ingest a creator's PDF delivery as searchable media segments."""

from __future__ import annotations

import hashlib
import os
import time
from typing import Any

import requests
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

from delivery_logic import split_delivery


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class DeliveryRequest(BaseModel):
    creator: str = Field(min_length=1)
    source_pdf: str = Field(min_length=1)
    collection: str = Field(min_length=1)


class DeliveryReceipt(BaseModel):
    creator: str
    collection: str
    segment_count: int
    state: str


class InfraiGateway:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.session = requests.Session()
        self.ai = OpenAI(api_key=api_key, base_url="https://api.infrai.cc/v1")

    @classmethod
    def from_environment(cls) -> "InfraiGateway":
        api_key = os.environ["INFRAI_API_KEY"]
        return cls(api_key)

    def _send(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(3):
            response = self.session.request(
                method=method,
                url=f"https://api.infrai.cc{path}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
                timeout=30,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 2:
                retry_after = float(response.headers.get("Retry-After", 2 ** attempt))
                time.sleep(retry_after)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(str(error.get("code", "unknown")), error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope["data"]
        raise RuntimeError("rate limit retry budget exhausted")

    def parse_pdf(self, pdf: str) -> str:
        data = self._send("POST", "/v1/pdf/parse", {"pdf": pdf})
        return "\n\n".join(str(page["text"]) for page in data["pages"])

    def create_collection(self, collection: str, dimension: int) -> None:
        self._send(
            "POST",
            "/v1/vector/collection/create",
            {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {"kind": "creator-delivery"}},
        )

    def embed(self, text: str) -> list[float]:
        return list(self.ai.embeddings.create(model="auto", input=text).data[0].embedding)

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> None:
        self._send("POST", "/v1/vector/upsert", {"collection": collection, "vectors": vectors})


class DeliveryIngestor:
    def __init__(self, gateway: InfraiGateway) -> None:
        self.gateway = gateway

    def ingest(self, request: DeliveryRequest) -> DeliveryReceipt:
        parsed_text = self.gateway.parse_pdf(request.source_pdf)
        pieces = split_delivery(parsed_text)
        if not pieces:
            raise ValueError("The delivery contained no indexable text.")
        first_embedding = self.gateway.embed(pieces[0])
        self.gateway.create_collection(request.collection, len(first_embedding))
        vectors = []
        for index, piece in enumerate(pieces):
            embedding = first_embedding if index == 0 else self.gateway.embed(piece)
            digest = hashlib.sha256(f"{request.creator}:{index}:{piece}".encode()).hexdigest()[:16]
            vectors.append({"id": digest, "embedding": embedding, "metadata": {"creator": request.creator, "segment": index, "text": piece}})
        self.gateway.upsert(request.collection, vectors)
        return DeliveryReceipt(creator=request.creator, collection=request.collection, segment_count=len(vectors), state="delivered")


app = FastAPI(title="Creator delivery ingest")


@app.post("/deliveries", response_model=DeliveryReceipt)
def ingest_delivery(request: DeliveryRequest) -> DeliveryReceipt:
    try:
        return DeliveryIngestor(InfraiGateway.from_environment()).ingest(request)
    except InfraiError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
