"""Data profiling engine."""

import json
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dasa.notebook.kernel import KernelManager


@dataclass
class ColumnProfile:
    """Profile of a single DataFrame column."""
    name: str
    dtype: str
    count: int
    unique_count: int
    null_count: int
    null_percent: float

    # Numeric columns
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None

    # Categorical columns
    top_values: Optional[list[tuple[str, int]]] = None

    # Issues detected
    issues: list[str] = field(default_factory=list)


@dataclass
class DataFrameProfile:
    """Complete profile of a DataFrame."""
    name: str
    shape: tuple[int, int]
    memory_bytes: int
    columns: list[ColumnProfile]
    issues: list[str] = field(default_factory=list)
    sample_rows: Optional[list[dict[str, Any]]] = None


PROFILE_CODE = '''
import json
import pandas as pd
import numpy as np

def _dasa_profile(df, var_name, sample_n=5):
    """Generate DataFrame profile."""
    profile = {{
        "name": var_name,
        "shape": list(df.shape),
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
        "columns": [],
        "issues": [],
        "sample_rows": df.head(sample_n).to_dict("records")
    }}

    for col in df.columns:
        col_data = df[col]
        col_profile = {{
            "name": col,
            "dtype": str(col_data.dtype),
            "count": int(len(col_data)),
            "unique_count": int(col_data.nunique()),
            "null_count": int(col_data.isnull().sum()),
            "null_percent": float(col_data.isnull().sum() / len(col_data) * 100),
            "issues": []
        }}

        # Numeric columns
        if pd.api.types.is_numeric_dtype(col_data):
            col_profile["min_value"] = float(col_data.min()) if not pd.isna(col_data.min()) else None
            col_profile["max_value"] = float(col_data.max()) if not pd.isna(col_data.max()) else None
            col_profile["mean_value"] = float(col_data.mean()) if not pd.isna(col_data.mean()) else None
            col_profile["std_value"] = float(col_data.std()) if not pd.isna(col_data.std()) else None

            # Check for issues
            if col_data.min() < 0 and col_data.max() > 0:
                neg_count = (col_data < 0).sum()
                if neg_count < len(col_data) * 0.1:  # Less than 10% negative
                    col_profile["issues"].append(f"{{neg_count}} negative values")

        # Categorical/object columns
        elif col_data.dtype == 'object' or str(col_data.dtype) == 'category':
            value_counts = col_data.value_counts().head(5)
            col_profile["top_values"] = [
                [str(k), int(v)] for k, v in value_counts.items()
            ]

        # Datetime columns
        elif pd.api.types.is_datetime64_any_dtype(col_data):
            col_profile["min_value"] = str(col_data.min())
            col_profile["max_value"] = str(col_data.max())

        # Check null percentage
        if col_profile["null_percent"] > 5:
            col_profile["issues"].append(f"{{col_profile['null_percent']:.1f}}% null")
            profile["issues"].append(f"{{col}}: {{col_profile['null_percent']:.1f}}% null")

        profile["columns"].append(col_profile)

    return profile

_dasa_result = _dasa_profile({var_name}, "{var_name}", {sample_n})
print(json.dumps(_dasa_result))
'''


class Profiler:
    """Data profiling engine."""

    def __init__(self, kernel: "KernelManager"):
        self.kernel = kernel

    def profile_dataframe(
        self,
        var_name: str,
        sample_n: int = 5
    ) -> DataFrameProfile:
        """Profile a DataFrame variable."""

        code = PROFILE_CODE.format(var_name=var_name, sample_n=sample_n)
        result = self.kernel.execute(code)

        if not result.success:
            raise RuntimeError(f"Failed to profile {var_name}: {result.error}")

        data = json.loads(result.stdout)

        columns = [
            ColumnProfile(
                name=c["name"],
                dtype=c["dtype"],
                count=c["count"],
                unique_count=c["unique_count"],
                null_count=c["null_count"],
                null_percent=c["null_percent"],
                min_value=c.get("min_value"),
                max_value=c.get("max_value"),
                mean_value=c.get("mean_value"),
                std_value=c.get("std_value"),
                top_values=c.get("top_values"),
                issues=c.get("issues", [])
            )
            for c in data["columns"]
        ]

        return DataFrameProfile(
            name=data["name"],
            shape=tuple(data["shape"]),
            memory_bytes=data["memory_bytes"],
            columns=columns,
            issues=data.get("issues", []),
            sample_rows=data.get("sample_rows")
        )

    def get_variable_type(self, var_name: str) -> str:
        """Get the type of a variable."""
        code = f"print(type({var_name}).__name__)"
        result = self.kernel.execute(code)

        if not result.success:
            raise NameError(f"Variable '{var_name}' not found")

        return result.stdout.strip()
