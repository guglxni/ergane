"""Distributed cache invalidation using vector clocks.

This module implements a novel protocol for maintaining consistent
 distributed cache state during network partitions using vector clocks
 and optimistic reconciliation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class VectorClock:
    """A vector clock for tracking event ordering across nodes."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.clock: Dict[str, int] = {node_id: 0}

    def increment(self) -> None:
        self.clock[self.node_id] += 1

    def merge(self, other: "VectorClock") -> None:
        for node, timestamp in other.clock.items():
            self.clock[node] = max(self.clock.get(node, 0), timestamp)

    def compare(self, other: "VectorClock") -> int:
        """Return -1 if self < other, 1 if self > other, 0 if concurrent."""
        dominates = False
        dominated = False
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        for node in all_nodes:
            a = self.clock.get(node, 0)
            b = other.clock.get(node, 0)
            if a > b:
                dominates = True
            elif b > a:
                dominated = True
        if dominates and not dominated:
            return 1
        if dominated and not dominates:
            return -1
        return 0


class DistributedCache:
    """Cache with vector-clock-based invalidation protocol."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.store: Dict[str, Tuple[Any, VectorClock]] = {}

    def put(self, key: str, value: Any) -> None:
        vc = VectorClock(self.node_id)
        vc.increment()
        self.store[key] = (value, vc)

    def invalidate(self, key: str, remote_vc: VectorClock) -> bool:
        """Invalidate if remote_vc is newer than local."""
        if key not in self.store:
            return False
        local_vc = self.store[key][1]
        comparison = local_vc.compare(remote_vc)
        if comparison == -1:
            del self.store[key]
            return True
        return False

    def reconcile(self, other: "DistributedCache") -> List[str]:
        """Reconcile cache state with another node after partition heals."""
        invalidated: List[str] = []
        for key, (value, vc) in other.store.items():
            if key in self.store:
                local_vc = self.store[key][1]
                comparison = local_vc.compare(vc)
                if comparison == -1:
                    self.store[key] = (value, vc)
                    invalidated.append(key)
                elif comparison == 0:
                    # Concurrent writes: deterministic tie-breaker by node_id
                    if other.node_id < self.node_id:
                        self.store[key] = (value, vc)
                        invalidated.append(key)
            else:
                self.store[key] = (value, vc)
        return invalidated
