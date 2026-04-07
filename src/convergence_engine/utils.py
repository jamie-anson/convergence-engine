from __future__ import annotations

import copy
import hashlib
import json
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def canonical_json(value: Any) -> str:
    if is_dataclass(value):
        value = asdict(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def get_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def merge_patch(target: Any, patch: Any) -> Any:
    """Apply RFC 7396 JSON Merge Patch without mutating the input."""
    if not isinstance(patch, dict):
        return copy.deepcopy(patch)

    if not isinstance(target, dict):
        target = {}
    else:
        target = copy.deepcopy(target)

    for key, value in patch.items():
        if value is None:
            target.pop(key, None)
        else:
            target[key] = merge_patch(target.get(key), value)
    return target

