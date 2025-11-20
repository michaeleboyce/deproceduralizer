import re
import logging
from typing import Any, Type, TypeVar
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

def clean_json_string(json_str: str) -> str:
    """
    Clean common JSON formatting issues from LLM responses.

    Fixes:
    - Trailing commas before closing braces/brackets
    - Missing commas between fields
    - Extra whitespace
    - Comments (though not valid JSON, some models add them)
    """
    # Remove comments (// and /* */ style)
    json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

    # Remove trailing commas (common LLM mistake)
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

    # Fix missing commas between fields (heuristic: newline between closing quote and opening quote)
    json_str = re.sub(r'"\s*\n\s*"', '",\n"', json_str)

    return json_str.strip()

def repair_json_structure(json_data: Any, response_model: Type[T]) -> Any:
    """
    Heuristically repair JSON structure to match response model.
    
    Common repairs:
    - If model expects object with single list field but got a list, wrap it.
    """
    # Only attempt repair if we got a list but expected a dict (Pydantic models are dicts in JSON)
    if isinstance(json_data, list):
        # Check if response_model has exactly one field that is a list
        fields = response_model.model_fields
        if len(fields) == 1:
            field_name = next(iter(fields))
            # We assume if it's a single field, it's likely the list wrapper we want
            # This is a safe heuristic for our specific use cases (ObligationsList, etc.)
            logger.debug(f"Repairing JSON: wrapping list in '{field_name}'")
            return {field_name: json_data}
            
    return json_data
