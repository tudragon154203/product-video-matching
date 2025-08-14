import json
from pathlib import Path
from typing import Dict, Any
from jsonschema import validate, ValidationError


class EventValidator:
    """Validates events against JSON schemas (supports dot- and underscore-style names)."""

    def __init__(self):
        self.schemas: Dict[str, Dict[str, Any]] = {}
        # Map dotted aliases (e.g., "image.embeddings.completed") to underscore schema keys
        self.aliases: Dict[str, str] = {}
        self._load_schemas()

    def _load_schemas(self):
        """Load all JSON schemas from the schemas directory"""
        schemas_dir = Path(__file__).parent / "schemas"

        for schema_file in schemas_dir.glob("*.json"):
            schema_key = schema_file.stem  # e.g., "image_embeddings_completed"
            with open(schema_file, "r", encoding="utf-8") as f:
                self.schemas[schema_key] = json.load(f)

            # Create a dotted alias for convenience: "image_embeddings_completed" -> "image.embeddings.completed"
            dotted_alias = schema_key.replace("_", ".")
            # Only set alias if there isn't already a real schema under that key
            if dotted_alias not in self.schemas and dotted_alias not in self.aliases:
                self.aliases[dotted_alias] = schema_key

    def _resolve_schema_key(self, event_type: str) -> str:
        """
        Resolve the schema key for a given event_type.
        Accepts either underscore ("image_embeddings_completed") or dotted ("image.embeddings.completed") forms.
        """
        # Exact match first
        if event_type in self.schemas:
            return event_type

        # Normalized underscore form
        normalized = event_type.replace(".", "_")
        if normalized in self.schemas:
            return normalized

        # Known dotted alias -> underscore key
        if event_type in self.aliases:
            return self.aliases[event_type]

        # Nothing matched
        raise ValueError(f"Unknown event type: {event_type}")

    def validate_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Validate an event against its schema.

        Args:
            event_type: The type of event (e.g., 'products_collect_request' or 'image.embeddings.completed')
            event_data: The event data to validate

        Returns:
            True if valid; raises ValidationError (or ValueError for unknown type) if invalid.
        """
        schema_key = self._resolve_schema_key(event_type)
        schema = self.schemas[schema_key]

        try:
            validate(instance=event_data, schema=schema)
            return True
        except ValidationError as e:
            raise ValidationError(f"Event validation failed for {event_type}: {e.message}")

    def get_schema(self, event_type: str) -> Dict[str, Any]:
        """Get the schema for a specific event type (supports dotted or underscore names)."""
        schema_key = self._resolve_schema_key(event_type)
        return self.schemas[schema_key]


# Global validator instance
validator = EventValidator()
