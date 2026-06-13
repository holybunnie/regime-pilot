#!/usr/bin/env python3
"""Canonical hashing for the commit-reveal attestation.

Recipe (must match the README and the verifier exactly):
    canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                ensure_ascii=False).encode('utf-8')
    commit_hash    = keccak256(canonical_json || salt)        # 32 bytes
    salt           = 32 cryptographically-random bytes (os.urandom)

`commit_hash` is what gets stored on-chain via SignalAttestor.commit(bytes32).
Anyone can recompute it from the revealed payload + salt and compare.
"""
import hashlib
import json
import os

from eth_utils import keccak


def canonical_json(payload: dict) -> bytes:
    """Deterministic JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def commit_hash(payload: dict, salt: bytes) -> bytes:
    """keccak256(canonical_json(payload) || salt). Returns 32 bytes."""
    if len(salt) != 32:
        raise ValueError("salt must be exactly 32 bytes")
    return keccak(canonical_json(payload) + salt)


def new_salt() -> bytes:
    """32 cryptographically random bytes."""
    return os.urandom(32)


def deterministic_salt(seed_hex: str, timestamp_utc: str) -> bytes:
    """Reproducible per-commit salt = keccak(seed || timestamp_utc).

    Lets ephemeral runners (GitHub Actions) commit without persisting salts: at reveal
    the same seed + timestamp regenerates the exact salt. The seed is a secret.
    """
    seed = bytes.fromhex(seed_hex[2:] if seed_hex.startswith("0x") else seed_hex)
    return keccak(seed + timestamp_utc.encode("utf-8"))


def universe_hash(universe_path) -> str:
    """sha256 hex of the canonical token-symbol list — pins the universe to the signal."""
    from pathlib import Path
    obj = json.loads(Path(universe_path).read_text())
    syms = sorted(t["symbol"] for t in obj["tokens"])
    return hashlib.sha256(canonical_json(syms)).hexdigest()


def spec_hash(spec_path) -> str:
    """sha256 hex of the canonical-JSON form of a spec file (stable across formatting)."""
    from pathlib import Path
    obj = json.loads(Path(spec_path).read_text())
    return hashlib.sha256(canonical_json(obj)).hexdigest()
