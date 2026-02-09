"""Data profiling by injecting profiling code into the kernel."""

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dasa.notebook.kernel import DasaKernelManager


@dataclass
class ColumnProfile:
    """Profile of a single column."""
    name: str
    dtype: str
    non_null_count: int
    total_count: int
    null_count: int
    null_percent: float
    unique_count: int
    # Numeric stats (optional)
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean_val: Optional[float] = None
    std_val: Optional[float] = None
    # Categorical stats (optional)
    top_values: Optional[list[str]] = None
    # Issues
    issues: list[str] = field(default_factory=list)


@dataclass
class DataFrameProfile:
    """Profile of a DataFrame."""
    name: str
    shape: tuple[int, int]
    memory_bytes: int
    columns: list[ColumnProfile]
    issues: list[str] = field(default_factory=list)
    sample_rows: Optional[list[dict]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "shape": list(self.shape),
            "memory_bytes": self.memory_bytes,
            "columns": {
                col.name: {
                    "dtype": col.dtype,
                    "non_null": col.non_null_count,
                    "null_count": col.null_count,
                    "null_percent": round(col.null_percent, 2),
                    "unique": col.unique_count,
                    **({"min": col.min_val, "max": col.max_val, "mean": round(col.mean_val, 4) if col.mean_val is not None else None, "std": round(col.std_val, 4) if col.std_val is not None else None} if col.min_val is not None else {}),
                    **({"top_values": col.top_values} if col.top_values else {}),
                    **({"issues": col.issues} if col.issues else {}),
                }
                for col in self.columns
            },
            "issues": self.issues,
        }


# Code injected into the kernel to profile a DataFrame
PROFILE_CODE = '''
import json as _json

def _dasa_profile(var_name, df):
    """Profile a DataFrame and return JSON."""
    result = {
        "name": var_name,
        "shape": list(df.shape),
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
        "columns": [],
    }

    for col in df.columns:
        series = df[col]
        col_info = {
            "name": str(col),
            "dtype": str(series.dtype),
            "non_null_count": int(series.count()),
            "total_count": len(series),
            "null_count": int(series.isna().sum()),
            "null_percent": round(float(series.isna().mean() * 100), 2),
            "unique_count": int(series.nunique()),
        }

        # Numeric stats
        if series.dtype.kind in ('i', 'f', 'u'):
            try:
                col_info["min_val"] = float(series.min())
                col_info["max_val"] = float(series.max())
                col_info["mean_val"] = float(series.mean())
                col_info["std_val"] = float(series.std())
            except (TypeError, ValueError):
                pass

        # Categorical / object stats
        if series.dtype == 'object' or series.dtype.name == 'category':
            try:
                top = series.value_counts().head(10)
                col_info["top_values"] = [str(v) for v in top.index.tolist()]
            except Exception:
                pass

        result["columns"].append(col_info)

    print(_json.dumps(result))

_dasa_profile("{var_name}", {var_name})
del _dasa_profile
'''


LIST_DATAFRAMES_CODE = '''
import json as _json
import pandas as _pd

_dfs = []
for _name, _obj in list(globals().items()):
    if not _name.startswith('_') and isinstance(_obj, _pd.DataFrame):
        _dfs.append({
            "name": _name,
            "shape": list(_obj.shape),
            "memory_mb": round(_obj.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        })
print(_json.dumps(_dfs))
del _dfs
'''


class Profiler:
    """Profile variables in kernel memory."""

    def __init__(self, kernel: DasaKernelManager):
        self.kernel = kernel

    def list_dataframes(self) -> list[dict]:
        """List all DataFrame variables in the kernel."""
        result = self.kernel.execute(LIST_DATAFRAMES_CODE, timeout=15)
        if not result.success:
            return []
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return []

    def profile_dataframe(self, var_name: str) -> DataFrameProfile:
        """Profile a DataFrame variable in the kernel."""
        code = PROFILE_CODE.replace("{var_name}", var_name)
        result = self.kernel.execute(code)

        if not result.success:
            raise RuntimeError(
                f"Failed to profile '{var_name}': {result.error_type}: {result.error}"
            )

        # Parse JSON from stdout
        try:
            data = json.loads(result.stdout.strip())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse profile output: {e}")

        return self._parse_profile(data)

    def _parse_profile(self, data: dict) -> DataFrameProfile:
        """Parse raw profile data into DataFrameProfile."""
        columns = []
        issues = []

        for col_data in data.get("columns", []):
            col_issues = []
            null_pct = col_data.get("null_percent", 0)
            if null_pct > 0:
                col_issues.append(f"{null_pct}% null values")

            # Check for negative values in numeric columns
            min_val = col_data.get("min_val")
            if min_val is not None and min_val < 0:
                col_issues.append("has negative values")

            if col_issues:
                issues.append(f"{col_data['name']}: {', '.join(col_issues)}")

            col = ColumnProfile(
                name=col_data["name"],
                dtype=col_data["dtype"],
                non_null_count=col_data["non_null_count"],
                total_count=col_data["total_count"],
                null_count=col_data["null_count"],
                null_percent=col_data["null_percent"],
                unique_count=col_data["unique_count"],
                min_val=col_data.get("min_val"),
                max_val=col_data.get("max_val"),
                mean_val=col_data.get("mean_val"),
                std_val=col_data.get("std_val"),
                top_values=col_data.get("top_values"),
                issues=col_issues,
            )
            columns.append(col)

        return DataFrameProfile(
            name=data["name"],
            shape=tuple(data["shape"]),
            memory_bytes=data.get("memory_bytes", 0),
            columns=columns,
            issues=issues,
        )


def profile_csv(file_path: str) -> DataFrameProfile:
    """Profile a CSV file directly without a kernel.

    Reads the file with the csv module + basic stats,
    avoiding a pandas/kernel dependency for quick profiling.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read the CSV
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            raise ValueError(f"Empty CSV file: {file_path}")

        rows: list[list[str]] = []
        for row in reader:
            rows.append(row)

    n_rows = len(rows)
    n_cols = len(header)
    columns: list[ColumnProfile] = []
    issues: list[str] = []

    for col_idx, col_name in enumerate(header):
        values = [row[col_idx] if col_idx < len(row) else "" for row in rows]
        non_empty = [v for v in values if v.strip()]
        null_count = n_rows - len(non_empty)
        null_pct = round(null_count / n_rows * 100, 2) if n_rows > 0 else 0
        unique_count = len(set(non_empty))

        col_issues: list[str] = []
        if null_pct > 0:
            col_issues.append(f"{null_pct}% null values")

        # Try to detect numeric columns
        min_val = max_val = mean_val = std_val = None
        top_values = None
        dtype = "object"

        numeric_vals: list[float] = []
        for v in non_empty:
            try:
                numeric_vals.append(float(v))
            except ValueError:
                break
        else:
            # All non-empty values are numeric
            if numeric_vals:
                dtype = "float64" if any("." in v for v in non_empty) else "int64"
                min_val = min(numeric_vals)
                max_val = max(numeric_vals)
                mean_val = sum(numeric_vals) / len(numeric_vals)
                variance = sum((x - mean_val) ** 2 for x in numeric_vals) / max(len(numeric_vals) - 1, 1)
                std_val = variance ** 0.5
                if min_val < 0:
                    col_issues.append("has negative values")

        if dtype == "object" and non_empty:
            # Get top values by frequency
            from collections import Counter
            counts = Counter(non_empty)
            top_values = [v for v, _ in counts.most_common(10)]

        if col_issues:
            issues.append(f"{col_name}: {', '.join(col_issues)}")

        columns.append(ColumnProfile(
            name=col_name,
            dtype=dtype,
            non_null_count=len(non_empty),
            total_count=n_rows,
            null_count=null_count,
            null_percent=null_pct,
            unique_count=unique_count,
            min_val=min_val,
            max_val=max_val,
            mean_val=mean_val,
            std_val=std_val,
            top_values=top_values,
            issues=col_issues,
        ))

    # Estimate memory (rough: 8 bytes per numeric, avg string length per object)
    memory_est = n_rows * n_cols * 8

    return DataFrameProfile(
        name=path.stem,
        shape=(n_rows, n_cols),
        memory_bytes=memory_est,
        columns=columns,
        issues=issues,
    )
