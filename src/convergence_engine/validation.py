from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from importlib import resources
from typing import Any


class SchemaValidationError(ValueError):
    """Raised when a runtime object does not satisfy a schema shape."""


def load_schema(name: str, *, version: str = "v1-lite") -> dict[str, Any]:
    resource = resources.files("convergence_engine").joinpath("schemas", version, f"{name}.schema.json")
    return json.loads(resource.read_text())


def validate_against_schema(value: Any, schema: dict[str, Any]) -> list[str]:
    plain = _to_plain(value)
    errors: list[str] = []
    _validate_subschema(plain, schema, path="$", errors=errors)
    return errors


def validate_named_schema(value: Any, name: str, *, version: str = "v1-lite") -> list[str]:
    return validate_against_schema(value, load_schema(name, version=version))


def assert_valid_named_schema(value: Any, name: str, *, version: str = "v1-lite") -> None:
    errors = validate_named_schema(value, name, version=version)
    if errors:
        raise SchemaValidationError("; ".join(errors))


def _to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value


def _validate_subschema(value: Any, schema: dict[str, Any], *, path: str, errors: list[str]) -> None:
    if "oneOf" in schema:
        option_errors: list[list[str]] = []
        for option in schema["oneOf"]:
            local_errors: list[str] = []
            _validate_subschema(value, option, path=path, errors=local_errors)
            if not local_errors:
                return
            option_errors.append(local_errors)
        errors.append(f"{path}: did not match any oneOf option")
        return

    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object")
            return
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key}: missing required property")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            for key in extra:
                errors.append(f"{path}.{key}: additional property not allowed")
        for key, subschema in properties.items():
            if key in value:
                _validate_subschema(value[key], subschema, path=f"{path}.{key}", errors=errors)
        return

    if expected_type == "string" and not isinstance(value, str):
        errors.append(f"{path}: expected string")
        return
    if expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path}: expected integer")
            return
    if expected_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{path}: expected number")
            return
    if expected_type == "boolean" and not isinstance(value, bool):
        errors.append(f"{path}: expected boolean")
        return
    if expected_type == "array" and not isinstance(value, list):
        errors.append(f"{path}: expected array")
        return
    if expected_type == "null" and value is not None:
        errors.append(f"{path}: expected null")
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']}")

    if "minimum" in schema and value is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < schema["minimum"]:
            errors.append(f"{path}: expected >= {schema['minimum']}")

