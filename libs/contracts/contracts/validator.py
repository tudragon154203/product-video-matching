import json
import os
from pathlib import Path
from typing import Dict, Any
import jsonschema
from jsonschema import validate, ValidationError


class EventValidator:
    """Validates events against JSON schemas"""
    
    def __init__(self):
        self.schemas = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """Load all JSON schemas from the schemas directory"""
        schemas_dir = Path(__file__).parent / "schemas"
        
        for schema_file in schemas_dir.glob("*.json"):
            schema_name = schema_file.stem
            with open(schema_file, 'r') as f:
                self.schemas[schema_name] = json.load(f)
    
    def validate_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Validate an event against its schema
        
        Args:
            event_type: The type of event (e.g., 'products_collect_request')
            event_data: The event data to validate
            
        Returns:
            True if valid, raises ValidationError if invalid
        """
        if event_type not in self.schemas:
            raise ValueError(f"Unknown event type: {event_type}")
        
        schema = self.schemas[event_type]
        
        try:
            validate(instance=event_data, schema=schema)
            return True
        except ValidationError as e:
            raise ValidationError(f"Event validation failed for {event_type}: {e.message}")
    
    def get_schema(self, event_type: str) -> Dict[str, Any]:
        """Get the schema for a specific event type"""
        if event_type not in self.schemas:
            raise ValueError(f"Unknown event type: {event_type}")
        return self.schemas[event_type]


# Global validator instance
validator = EventValidator()