# Mock pandas.api.types subpackage for type inspections

def is_list_like(obj) -> bool:
    """Check if object is iterable but not a string/bytes."""
    return hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes))

def is_scalar(obj) -> bool:
    """Check if object is a scalar (not list-like)."""
    return not is_list_like(obj)

def is_array_like(obj) -> bool:
    """Check if object behaves like an array."""
    return hasattr(obj, '__array__') or is_list_like(obj)

def is_float(obj) -> bool:
    """Check if object behaves like a float."""
    return isinstance(obj, float) or type(obj).__name__ in ('float32', 'float64')

def infer_dtype(obj, skipna: bool = True) -> str:
    """
    Infer the string representation of type from a list-like collection.
    Matches pandas.api.types.infer_dtype returns.
    """
    if not is_list_like(obj):
        return "mixed"
        
    non_null_elems = [x for x in obj if x is not None]
    if not non_null_elems:
        return "mixed"
        
    first = non_null_elems[0]
    if isinstance(first, bool):
        return "boolean"
    elif isinstance(first, int):
        return "integer"
    elif isinstance(first, float) or type(first).__name__ in ('float32', 'float64'):
        return "floating"
    elif isinstance(first, str):
        return "string"
    elif isinstance(first, bytes):
        return "bytes"
    return "mixed"
