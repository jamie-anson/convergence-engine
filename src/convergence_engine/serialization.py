from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any


def to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: to_plain_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    return value


def serialize_store(store: Any) -> dict[str, Any]:
    return {
        "run": to_plain_data(store.run),
        "states": [to_plain_data(item) for item in store.states],
        "proposals": [to_plain_data(item) for item in store.proposals],
        "constraints": [to_plain_data(item) for item in store.constraints],
        "trail": [to_plain_data(item) for item in store.trail],
        "evaluations": [to_plain_data(item) for item in store.evaluations],
    }


def serialize_engine(engine: Any) -> dict[str, Any]:
    return serialize_store(engine.store)


def to_json(value: Any, *, indent: int | None = 2) -> str:
    return json.dumps(to_plain_data(value), indent=indent, sort_keys=True, ensure_ascii=False)

