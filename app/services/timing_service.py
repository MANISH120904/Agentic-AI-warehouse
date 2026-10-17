"""In-process execution timing for low-latency visibility (hackathon telemetry)."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict


class TimingService:
    """Tracks recent request/tool durations without external APM."""

    def __init__(self, maxlen: int = 200) -> None:
        self._lock = threading.Lock()
        self._samples: Deque[dict[str, Any]] = deque(maxlen=maxlen)

    def record(self, name: str, duration_ms: float, *, ok: bool = True) -> None:
        with self._lock:
            self._samples.append(
                {
                    "name": name,
                    "duration_ms": round(duration_ms, 2),
                    "ok": ok,
                    "ts": time.time(),
                }
            )

    def summary(self) -> dict[str, Any]:
        with self._lock:
            samples = list(self._samples)
        if not samples:
            return {
                "sample_count": 0,
                "avg_ms": 0.0,
                "p95_ms": 0.0,
                "max_ms": 0.0,
                "low_latency_target_ms": 500,
                "within_target_ratio": 1.0,
                "by_name": {},
            }

        durations = sorted(float(s["duration_ms"]) for s in samples)
        avg = sum(durations) / len(durations)
        p95_index = max(0, int(len(durations) * 0.95) - 1)
        target = 500.0
        within = sum(1 for d in durations if d <= target) / len(durations)

        by_name: Dict[str, list[float]] = {}
        for sample in samples:
            by_name.setdefault(str(sample["name"]), []).append(float(sample["duration_ms"]))

        return {
            "sample_count": len(durations),
            "avg_ms": round(avg, 2),
            "p95_ms": round(durations[p95_index], 2),
            "max_ms": round(durations[-1], 2),
            "low_latency_target_ms": target,
            "within_target_ratio": round(within, 3),
            "by_name": {
                name: {
                    "count": len(values),
                    "avg_ms": round(sum(values) / len(values), 2),
                }
                for name, values in by_name.items()
            },
        }


timing_service = TimingService()
