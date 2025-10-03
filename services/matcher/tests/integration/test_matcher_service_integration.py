"""Integration tests for matcher service using in-memory dependencies."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import math
import sys
import types
from typing import Any, Dict, List, Optional

import pytest

numpy_stub = types.ModuleType("numpy")

def _to_float_list(data: Any) -> List[float]:
    if isinstance(data, (list, tuple)):
        return [float(value) for value in data]
    return [float(data)]

def _array(data: Any, dtype: Any = None) -> List[float]:
    return _to_float_list(data)

def _dot(vec1: List[float], vec2: List[float]) -> float:
    return sum(a * b for a, b in zip(vec1, vec2))

def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0

class _LinalgModule:
    @staticmethod
    def norm(vec: List[float]) -> float:
        return math.sqrt(sum(value * value for value in vec))

numpy_stub.array = _array
numpy_stub.dot = _dot
numpy_stub.mean = _mean
numpy_stub.float32 = float
numpy_stub.linalg = _LinalgModule()
numpy_stub.ndarray = list


def _isscalar(obj: Any) -> bool:
    return isinstance(obj, (int, float))

numpy_stub.isscalar = _isscalar
numpy_stub.bool_ = bool
sys.modules.setdefault("numpy", numpy_stub)

asyncpg_stub = types.ModuleType("asyncpg")


class _AsyncpgPool:
    async def close(self) -> None:  # pragma: no cover - defensive stub
        return None


async def _create_pool(*_: Any, **__: Any) -> _AsyncpgPool:
    raise RuntimeError("asyncpg stub should not create pools in tests")


asyncpg_stub.Pool = _AsyncpgPool
asyncpg_stub.create_pool = _create_pool
sys.modules.setdefault("asyncpg", asyncpg_stub)
pydantic_stub = types.ModuleType("pydantic")

class _BaseModel:
    def __init__(self, **data: Any) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    def dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)

pydantic_stub.BaseModel = _BaseModel
sys.modules.setdefault("pydantic", pydantic_stub)

aio_pika_stub = types.ModuleType("aio_pika")

class _ExchangeType:
    TOPIC = "topic"

class _DeliveryMode:
    PERSISTENT = 2

class _Message:
    def __init__(
        self,
        body: bytes,
        headers: Dict[str, Any] | None = None,
        delivery_mode: int | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.body = body
        self.headers = headers or {}
        self.delivery_mode = delivery_mode
        self.correlation_id = correlation_id

async def _connect_robust(*_: Any, **__: Any) -> Any:
    raise RuntimeError("aio_pika stub should not establish connections in tests")

class _Exchange:
    async def publish(self, message: _Message, routing_key: str) -> None:
        return None

class _IncomingMessage:
    def __init__(
        self,
        body: bytes,
        headers: Dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.body = body
        self.headers = headers or {}
        self.correlation_id = correlation_id

    async def ack(self) -> None:
        return None

aio_pika_stub.ExchangeType = _ExchangeType
aio_pika_stub.DeliveryMode = _DeliveryMode
aio_pika_stub.Message = _Message
aio_pika_stub.IncomingMessage = _IncomingMessage
aio_pika_stub.Exchange = _Exchange
aio_pika_stub.connect_robust = _connect_robust
sys.modules.setdefault("aio_pika", aio_pika_stub)

from services.service import MatcherService

pytestmark = pytest.mark.integration


@dataclass
class PublishedEvent:
    """Record of a published event for assertions."""

    topic: str
    event_data: Dict[str, Any]
    correlation_id: Optional[str]


class InMemoryMessageBroker:
    """Simplified message broker that records published events."""

    def __init__(self) -> None:
        self.published_events: List[PublishedEvent] = []

    async def publish_event(
        self,
        topic: str,
        event_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> None:
        self.published_events.append(
            PublishedEvent(topic, event_data, correlation_id)
        )


@dataclass
class InMemoryDatabaseManager:
    """In-memory database manager that mimics asyncpg operations."""

    products: List[Dict[str, Any]] = field(default_factory=list)
    videos: List[Dict[str, Any]] = field(default_factory=list)
    product_images: List[Dict[str, Any]] = field(default_factory=list)
    video_frames: List[Dict[str, Any]] = field(default_factory=list)
    processed_events: Dict[str, str] = field(default_factory=dict)
    matches: List[Dict[str, Any]] = field(default_factory=list)

    async def connect(self) -> None:  # pragma: no cover - simple setup
        return None

    async def disconnect(self) -> None:  # pragma: no cover - simple teardown
        return None

    async def fetch_all(self, query: str, *args: Any) -> List[Dict[str, Any]]:
        normalized_query = " ".join(query.lower().split())

        if "from products" in normalized_query:
            job_id = args[0]
            return [
                {"product_id": product["product_id"], "title": product["title"]}
                for product in self.products
                if product["job_id"] == job_id
            ]

        if "from videos" in normalized_query:
            job_id = args[0]
            return [
                {"video_id": video["video_id"], "title": video["title"]}
                for video in self.videos
                if video["job_id"] == job_id
            ]

        if "from product_images" in normalized_query:
            product_id = args[0]
            return [
                image
                for image in self.product_images
                if image["product_id"] == product_id
            ]

        if "from video_frames" in normalized_query:
            video_id = args[0]
            frames = [
                frame
                for frame in self.video_frames
                if frame["video_id"] == video_id
            ]
            return sorted(frames, key=lambda frame: frame["ts"])

        if "from temp_video_embeddings" in normalized_query:
            return []

        raise NotImplementedError(f"Unsupported fetch_all query: {query}")

    async def fetch_val(self, query: str, *args: Any) -> Any:
        normalized_query = " ".join(query.lower().split())

        if "select 1 from processed_events" in normalized_query:
            event_id = args[0]
            return 1 if event_id in self.processed_events else None

        if "insert into matches" in normalized_query:
            match_record = {
                "match_id": args[0],
                "job_id": args[1],
                "product_id": args[2],
                "video_id": args[3],
                "best_img_id": args[4],
                "best_frame_id": args[5],
                "ts": args[6],
                "score": args[7],
                "evidence_path": args[8],
            }
            self.matches.append(match_record)
            return match_record["match_id"]

        raise NotImplementedError(f"Unsupported fetch_val query: {query}")

    async def fetch_one(self, query: str, *args: Any) -> Optional[Dict[str, Any]]:
        normalized_query = " ".join(query.lower().split())

        if "select * from matches" in normalized_query:
            match_id = args[0]
            for match in self.matches:
                if match["match_id"] == match_id:
                    return match
            return None

        raise NotImplementedError(f"Unsupported fetch_one query: {query}")

    async def execute(self, query: str, *args: Any) -> str:
        normalized_query = " ".join(query.lower().split())

        if "insert into processed_events" in normalized_query:
            event_id, event_type = args
            self.processed_events.setdefault(event_id, event_type)
            return "INSERT 0 1"

        if "drop table if exists temp_video_embeddings" in normalized_query:
            return "DROP TABLE"

        if "create temp table temp_video_embeddings" in normalized_query:
            return "CREATE TABLE"

        raise NotImplementedError(f"Unsupported execute query: {query}")

    async def executemany(self, query: str, args: List[Any]) -> None:
        normalized_query = " ".join(query.lower().split())

        if "insert into temp_video_embeddings" in normalized_query:
            return None

        raise NotImplementedError(f"Unsupported executemany query: {query}")


def _create_matcher_service() -> tuple[MatcherService, InMemoryMessageBroker, InMemoryDatabaseManager]:
    broker = InMemoryMessageBroker()
    db = InMemoryDatabaseManager()
    service = MatcherService(
        db=db,
        broker=broker,
        data_root="/tmp",
    )
    asyncio.run(service.initialize())
    return service, broker, db


def test_handle_match_request_end_to_end() -> None:
    service, broker, db = _create_matcher_service()

    job_id = "job-123"
    event_id = "event-abc"
    product_id = "product-1"
    video_id = "video-1"

    embedding = [0.1, 0.2, 0.3]

    db.products.append(
        {"product_id": product_id, "title": "Test Product", "job_id": job_id}
    )
    db.videos.append(
        {"video_id": video_id, "title": "Test Video", "job_id": job_id}
    )
    db.product_images.append(
        {
            "img_id": "img-1",
            "product_id": product_id,
            "local_path": "product/img-1.jpg",
            "emb_rgb": None,
            "emb_gray": embedding,
            "kp_blob_path": "product/img-1.kp",
        }
    )
    db.video_frames.append(
        {
            "frame_id": "frame-1",
            "video_id": video_id,
            "ts": 1.5,
            "local_path": "video/frame-1.jpg",
            "emb_rgb": None,
            "emb_gray": embedding,
            "kp_blob_path": "video/frame-1.kp",
        }
    )

    try:
        asyncio.run(
            service.handle_match_request({"job_id": job_id, "event_id": event_id})
        )

        assert len(db.matches) == 1
        stored_match = db.matches[0]
        assert stored_match["job_id"] == job_id
        assert stored_match["product_id"] == product_id
        assert stored_match["video_id"] == video_id
        assert stored_match["best_img_id"] == "img-1"
        assert stored_match["best_frame_id"] == "frame-1"
        assert stored_match["score"] > 0.9

        assert event_id in db.processed_events
        assert db.processed_events[event_id] == "match.request"

        assert len(broker.published_events) == 2
        match_event = broker.published_events[0]
        assert match_event.topic == "match.result"
        assert match_event.event_data["job_id"] == job_id
        assert match_event.event_data["product_id"] == product_id
        assert match_event.event_data["video_id"] == video_id
        assert match_event.event_data["score"] == pytest.approx(
            stored_match["score"],
            rel=1e-6,
        )
        assert match_event.event_data["best_pair"]["img_id"] == "img-1"
        assert match_event.event_data["best_pair"]["frame_id"] == "frame-1"

        completion_event = broker.published_events[1]
        assert completion_event.topic == "matchings.process.completed"
        assert completion_event.event_data == {"job_id": job_id, "event_id": event_id}

        asyncio.run(
            service.handle_match_request({"job_id": job_id, "event_id": event_id})
        )

        assert len(db.matches) == 1
        assert len(broker.published_events) == 2
    finally:
        asyncio.run(service.cleanup())
