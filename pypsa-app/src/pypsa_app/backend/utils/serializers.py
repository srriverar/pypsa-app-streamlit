"""Serialization utilities for converting data structures to JSON"""

import math
from typing import Any

import pandas as pd


def serialize_df(data: pd.DataFrame | pd.Series) -> dict:
    """Convert pandas DataFrame or Series to JSON-serializable dict"""
    if isinstance(data, pd.DataFrame):
        result = data.to_dict(orient="split")
        # Convert tuple indices/columns to strings
        if result.get("index") and isinstance(
            result["index"][0] if result["index"] else None, tuple
        ):
            result["index"] = [str(idx) for idx in result["index"]]
        if result.get("columns") and isinstance(
            result["columns"][0] if result["columns"] else None, tuple
        ):
            result["columns"] = [str(col) for col in result["columns"]]
        return result
    elif isinstance(data, pd.Series):
        return {str(k): v for k, v in data.to_dict().items()}
    else:
        msg = f"Expected DataFrame or Series, got {type(data)}"
        raise TypeError(msg)


def sanitize_metadata(data: Any) -> Any:
    """Recursively sanitize metadata to be JSON-compatible (removes inf/nan)"""
    if isinstance(data, dict):
        return {k: sanitize_metadata(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_metadata(item) for item in data]
    elif isinstance(data, float) and (math.isinf(data) or math.isnan(data)):
        return None
    return data
