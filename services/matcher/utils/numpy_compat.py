"""Compatibility layer for NumPy usage within the matcher service."""

from __future__ import annotations

from math import sqrt
from typing import Iterable, Sequence

try:  # pragma: no cover - executed when NumPy is available
    import numpy as _np
except ImportError:  # pragma: no cover - triggered in minimal test environments

    class _FallbackNumpy:
        """Provide a very small subset of :mod:`numpy` for local testing."""

        float32 = float
        ndarray = list

        @staticmethod
        def array(values: Iterable[float], dtype: object | None = None) -> list[float]:
            del dtype  # The lightweight fallback treats all values as ``float``.
            if isinstance(values, Sequence):
                return [float(value) for value in values]
            return [float(value) for value in list(values)]

        @staticmethod
        def dot(vec1: Sequence[float], vec2: Sequence[float]) -> float:
            return sum(a * b for a, b in zip(vec1, vec2))

        class linalg:  # type: ignore[valid-type]
            @staticmethod
            def norm(vec: Sequence[float]) -> float:
                return sqrt(sum(value * value for value in vec))

        @staticmethod
        def mean(values: Sequence[float]) -> float:
            return sum(values) / len(values) if values else 0.0

    np = _FallbackNumpy()  # type: ignore[assignment]
else:
    np = _np

__all__ = ["np"]
