from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

# JSON Schema for config.yaml
CONFIG_SCHEMA: dict = {
    "type": "object",
    "required": ["providers"],
    "properties": {
        "providers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "endpoint"],
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^[a-z0-9][a-z0-9_-]*$",
                        "minLength": 1,
                    },
                    "endpoint": {
                        "type": "string",
                        "format": "uri",
                        "minLength": 1,
                    },
                    "api_key": {"type": ["string", "null"]},
                    "models": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name"],
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "deployment": {
                                    "type": "string",
                                    "enum": ["cloud", "local", "hybrid"],
                                },
                                "context_window": {
                                    "type": "integer",
                                    "minimum": 1,
                                },
                                "cost_input_1k": {
                                    "type": "number",
                                    "minimum": 0,
                                },
                                "cost_output_1k": {
                                    "type": "number",
                                    "minimum": 0,
                                },
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        }
    },
}


@dataclass(slots=True)
class ValidationResult:
    """配置校验结果."""

    valid: bool
    errors: list[str] = field(default_factory=list)


def _is_uri(instance: object) -> bool:
    """Check if instance is a valid URI."""
    if not isinstance(instance, str):
        return True
    try:
        result = urlparse(instance)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_config(config: dict) -> ValidationResult:
    """校验配置字典是否符合 Schema."""
    format_checker = FormatChecker()
    format_checker.checks("uri")(_is_uri)
    validator = Draft202012Validator(CONFIG_SCHEMA, format_checker=format_checker)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(config), key=lambda e: e.path):
        path = ".".join(str(p) for p in error.path) if error.path else "(root)"
        errors.append(f"{path}: {error.message}")
    return ValidationResult(valid=len(errors) == 0, errors=errors)
