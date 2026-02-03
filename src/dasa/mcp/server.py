"""MCP server implementation for DASA tools."""

import json
from typing import Any, Optional

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import KernelManager
from dasa.analysis.profiler import Profiler
from dasa.analysis.state import StateAnalyzer
from dasa.analysis.deps import DependencyAnalyzer


class DASAServer:
    """DASA MCP Server providing notebook tools."""

    def __init__(self):
        self.name = "dasa"
        self.version = "0.1.0"
        self._kernels: dict[str, KernelManager] = {}

    def get_tools(self) -> list[dict[str, Any]]:
        """Return list of available tools."""
        return [
            {
                "name": "profile",
                "description": "Profile a DataFrame variable in a notebook",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "notebook": {"type": "string", "description": "Path to notebook"},
                        "var": {"type": "string", "description": "Variable name to profile"},
                        "sample": {"type": "integer", "description": "Number of sample rows", "default": 5}
                    },
                    "required": ["notebook", "var"]
                }
            },
            {
                "name": "validate",
                "description": "Check notebook state for consistency issues",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "notebook": {"type": "string", "description": "Path to notebook"}
                    },
                    "required": ["notebook"]
                }
            },
            {
                "name": "deps",
                "description": "Analyze cell dependencies in a notebook",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "notebook": {"type": "string", "description": "Path to notebook"},
                        "cell": {"type": "integer", "description": "Show impact of modifying this cell"}
                    },
                    "required": ["notebook"]
                }
            },
            {
                "name": "run",
                "description": "Execute notebook cells",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "notebook": {"type": "string", "description": "Path to notebook"},
                        "cell": {"type": "integer", "description": "Cell index to run"},
                        "all": {"type": "boolean", "description": "Run all cells"}
                    },
                    "required": ["notebook"]
                }
            },
            {
                "name": "info",
                "description": "Show notebook metadata",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "notebook": {"type": "string", "description": "Path to notebook"}
                    },
                    "required": ["notebook"]
                }
            },
            {
                "name": "cells",
                "description": "List all cells in a notebook",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "notebook": {"type": "string", "description": "Path to notebook"},
                        "code_only": {"type": "boolean", "description": "Show only code cells"}
                    },
                    "required": ["notebook"]
                }
            },
            {
                "name": "replay",
                "description": "Run notebook from scratch and verify reproducibility",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "notebook": {"type": "string", "description": "Path to notebook"},
                        "compare": {"type": "boolean", "description": "Compare outputs", "default": True}
                    },
                    "required": ["notebook"]
                }
            }
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool with arguments."""
        handlers = {
            "profile": self._handle_profile,
            "validate": self._handle_validate,
            "deps": self._handle_deps,
            "run": self._handle_run,
            "replay": self._handle_replay,
            "info": self._handle_info,
            "cells": self._handle_cells,
        }

        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}

        try:
            return await handler(arguments)
        except Exception as e:
            return {"error": str(e)}

    async def _handle_profile(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle profile tool call."""
        notebook = args["notebook"]
        var = args["var"]
        sample = args.get("sample", 5)

        adapter = JupyterAdapter(notebook)
        kernel = self._get_kernel(notebook, adapter)

        try:
            # Execute cells to populate state
            for cell in adapter.code_cells:
                if cell.execution_count:
                    kernel.execute(cell.source)

            profiler = Profiler(kernel)
            var_type = profiler.get_variable_type(var)

            if var_type == "DataFrame":
                profile = profiler.profile_dataframe(var, sample)
                return {
                    "name": profile.name,
                    "shape": profile.shape,
                    "columns": [
                        {
                            "name": c.name,
                            "dtype": c.dtype,
                            "null_percent": c.null_percent,
                            "issues": c.issues
                        }
                        for c in profile.columns
                    ],
                    "issues": profile.issues,
                    "sample": profile.sample_rows
                }
            else:
                return {"type": var_type, "message": "Only DataFrame profiling is supported"}

        finally:
            self._release_kernel(notebook)

    async def _handle_validate(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle validate tool call."""
        notebook = args["notebook"]

        adapter = JupyterAdapter(notebook)
        analyzer = StateAnalyzer()
        analysis = analyzer.analyze(adapter)

        return {
            "is_consistent": analysis.is_consistent,
            "issues": [
                {
                    "severity": i.severity,
                    "cell": i.cell_index,
                    "message": i.message,
                    "suggestion": i.suggestion
                }
                for i in analysis.issues
            ],
            "execution_order": analysis.execution_order
        }

    async def _handle_deps(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle deps tool call."""
        notebook = args["notebook"]
        cell = args.get("cell")

        adapter = JupyterAdapter(notebook)
        analyzer = DependencyAnalyzer()
        graph = analyzer.build_graph(adapter)

        result = {
            "cells": [
                {
                    "index": node.index,
                    "preview": node.preview,
                    "definitions": list(node.definitions),
                    "upstream": list(node.upstream),
                    "downstream": list(node.downstream)
                }
                for node in graph.nodes.values()
            ]
        }

        if cell is not None:
            result["impact"] = {
                "cell": cell,
                "affected": graph.get_downstream(cell)
            }

        return result

    async def _handle_run(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle run tool call."""
        notebook = args["notebook"]
        cell = args.get("cell")
        run_all = args.get("all", False)

        adapter = JupyterAdapter(notebook)
        kernel = self._get_kernel(notebook, adapter)

        results = []

        try:
            cells_to_run = []
            if cell is not None:
                cells_to_run = [c for c in adapter.code_cells if c.index == cell]
            elif run_all:
                cells_to_run = adapter.code_cells

            for c in cells_to_run:
                result = kernel.execute(c.source)
                results.append({
                    "cell": c.index,
                    "success": result.success,
                    "stdout": result.stdout[:1000] if result.stdout else "",
                    "error": result.error
                })

            return {"results": results}

        finally:
            self._release_kernel(notebook)

    async def _handle_replay(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle replay tool call."""
        notebook = args["notebook"]
        compare = args.get("compare", True)

        adapter = JupyterAdapter(notebook)
        kernel = KernelManager(adapter.kernel_spec or "python3")

        results = []
        issues = []

        try:
            kernel.start()

            for cell in adapter.code_cells:
                result = kernel.execute(cell.source)

                cell_result = {
                    "cell": cell.index,
                    "success": result.success,
                    "output_match": True
                }

                if not result.success:
                    cell_result["error"] = f"{result.error_type}: {result.error}"
                    issues.append({
                        "cell": cell.index,
                        "type": "execution_error",
                        "message": result.error
                    })

                results.append(cell_result)

        finally:
            kernel.shutdown()

        total = len(results)
        succeeded = sum(1 for r in results if r["success"])
        score = (succeeded / total * 100) if total > 0 else 0

        return {
            "results": results,
            "issues": issues,
            "summary": {
                "total": total,
                "succeeded": succeeded,
                "reproducibility_score": round(score, 1)
            }
        }

    async def _handle_info(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle info tool call."""
        from pathlib import Path
        from dasa.analysis.parser import parse_cell

        notebook = args["notebook"]
        path = Path(notebook)
        adapter = JupyterAdapter(notebook)

        # Extract imports
        imports = set()
        for cell in adapter.code_cells:
            analysis = parse_cell(cell.source)
            imports.update(analysis.imports)

        return {
            "name": path.name,
            "kernel": adapter.kernel_spec,
            "cells": {
                "total": len(adapter.cells),
                "code": sum(1 for c in adapter.cells if c.cell_type == "code"),
                "markdown": sum(1 for c in adapter.cells if c.cell_type == "markdown")
            },
            "packages": sorted(list(imports))
        }

    async def _handle_cells(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle cells tool call."""
        from dasa.analysis.parser import parse_cell

        notebook = args["notebook"]
        code_only = args.get("code_only", False)

        adapter = JupyterAdapter(notebook)

        cells = []
        for cell in adapter.cells:
            if code_only and cell.cell_type != "code":
                continue

            cell_data = {
                "index": cell.index,
                "type": cell.cell_type,
                "preview": cell.preview
            }

            if cell.cell_type == "code":
                analysis = parse_cell(cell.source)
                cell_data["defines"] = list(analysis.definitions)[:5]

            cells.append(cell_data)

        return {"cells": cells}

    def _get_kernel(self, notebook: str, adapter: JupyterAdapter) -> KernelManager:
        """Get or create kernel for notebook."""
        if notebook not in self._kernels:
            kernel = KernelManager(adapter.kernel_spec or "python3")
            kernel.start()
            self._kernels[notebook] = kernel
        return self._kernels[notebook]

    def _release_kernel(self, notebook: str) -> None:
        """Release kernel for notebook."""
        if notebook in self._kernels:
            self._kernels[notebook].shutdown()
            del self._kernels[notebook]


def create_server() -> DASAServer:
    """Create a new DASA MCP server instance."""
    return DASAServer()
