"""Deterministic seeds: one per model call from (sample seed, step), and one
per sample from (campaign seed, sample id). Never a constant, and never derived
from the served text, so two cells of a contrast draw identically."""

from __future__ import annotations

import hashlib


def derive_seed(seed_base: int, step: int) -> int:
    h = hashlib.sha256(f"{seed_base}:{step}".encode()).digest()
    return int.from_bytes(h[:4], "big")


def sample_seed(campaign_seed: int, sample_id: str) -> int:
    h = hashlib.sha256(f"{campaign_seed}:{sample_id}".encode()).digest()
    return int.from_bytes(h[:4], "big")
