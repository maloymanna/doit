# src/doit/core/json_validator.py [NEW v1]
import json
import re
from typing import Dict, Any
try:
    import jsonschema
except ImportError:
    raise RuntimeError("Install jsonschema: pip install jsonschema")

class ValidationError(Exception):
    def __init__(self, message: str, raw: str):
        self.message = message
        self.raw = raw
        super().__init__(message)

class JSONValidator:
    MARKDOWN_BLOCK = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

    @staticmethod
    def extract_json(raw: str) -> str:
        raw = raw.strip()
        match = JSONValidator.MARKDOWN_BLOCK.search(raw)
        if match:
            return match.group(1).strip()
        
        # Fallback: find first { to last }
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return raw[start:end+1]
        raise ValidationError("No JSON object found", raw)

    def parse_and_validate(self, raw: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        try:
            json_str = self.extract_json(raw)
            data = json.loads(json_str)
            jsonschema.validate(instance=data, schema=schema)
            return data
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON syntax: {e}", raw)
        except jsonschema.ValidationError as e:
            raise ValidationError(f"Schema violation: {e.message}", raw)