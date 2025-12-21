"""Helper utilities for working with intent models."""

from typing import Dict, Any, List, Optional


def get_entity_by_name(intent: Dict[str, Any], entity_name: str) -> Optional[Dict[str, Any]]:
    """Get an entity from primary_entities list by name.
    
    Args:
        intent: The intent dictionary
        entity_name: The name of the entity to find
        
    Returns:
        The entity dictionary if found, None otherwise
    """
    primary_entities = intent.get("primary_entities", [])
    for entity in primary_entities:
        if entity.get("name") == entity_name:
            return entity
    return None


def get_operations_for_entity(intent: Dict[str, Any], entity_name: str) -> List[str]:
    """Get the operations list for a specific entity.
    
    Args:
        intent: The intent dictionary
        entity_name: The name of the entity
        
    Returns:
        List of operation strings (e.g., ['create', 'read', 'update', 'delete'])
        Returns empty list if entity not found in operations
    """
    operations = intent.get("operations", [])
    for op in operations:
        if op.get("entity_name") == entity_name:
            return op.get("operations", [])
    return []


def primary_entities_to_dict(intent: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Convert primary_entities list to dictionary format.
    
    This is useful for backward compatibility with code that expects
    the old dictionary format.
    
    Args:
        intent: The intent dictionary with primary_entities as a list
        
    Returns:
        Dictionary mapping entity names to entity definitions
    """
    primary_entities = intent.get("primary_entities", [])
    result = {}
    for entity in primary_entities:
        name = entity.get("name")
        if name:
            # Create a copy without the 'name' field
            entity_data = {k: v for k, v in entity.items() if k != "name"}
            result[name] = entity_data
    return result


def operations_to_dict(intent: Dict[str, Any]) -> Dict[str, List[str]]:
    """Convert operations list to dictionary format.
    
    This is useful for backward compatibility with code that expects
    the old dictionary format.
    
    Args:
        intent: The intent dictionary with operations as a list
        
    Returns:
        Dictionary mapping entity names to operation lists
    """
    operations = intent.get("operations", [])
    result = {}
    for op in operations:
        entity_name = op.get("entity_name")
        ops_list = op.get("operations", [])
        if entity_name:
            result[entity_name] = ops_list
    return result


def fields_to_dict(entity: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Convert entity fields list to dictionary format.
    
    Args:
        entity: The entity dictionary with fields as a list
        
    Returns:
        Dictionary mapping field names to field definitions
    """
    fields = entity.get("fields", [])
    result = {}
    for field in fields:
        name = field.get("name")
        if name:
            # Create a copy without the 'name' field
            field_data = {k: v for k, v in field.items() if k != "name"}
            result[name] = field_data
    return result
