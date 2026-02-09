"""DASA MCP server — expose tools via Model Context Protocol.

Usage:
    dasa mcp-serve

Configuration (for any MCP-compatible agent):
    {
        "mcpServers": {
            "dasa": {
                "command": "dasa",
                "args": ["mcp-serve"]
            }
        }
    }
"""

import json
import sys
from typing import Optional


def create_mcp_server():
    """Create and configure the MCP server.

    Returns the server instance, or None if mcp package is not installed.
    """
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
    except ImportError:
        return None

    server = Server("dasa")

    @server.tool("profile")
    async def profile_tool(notebook: str, var: str) -> str:
        """Profile a variable in the notebook kernel.

        Returns column names, types, statistics, and data quality issues.
        Auto-caches the profile to .dasa/profiles/.
        """
        from dasa.notebook.jupyter import JupyterAdapter
        from dasa.notebook.kernel import DasaKernelManager
        from dasa.analysis.profiler import Profiler
        from dasa.session.profiles import ProfileCache
        from dasa.session.log import SessionLog

        adapter = JupyterAdapter(notebook)
        kernel = DasaKernelManager()
        try:
            kernel.start()
            for cell in adapter.code_cells:
                if cell.execution_count is not None:
                    kernel.execute(cell.source, timeout=60)

            profiler = Profiler(kernel)
            df_profile = profiler.profile_dataframe(var)

            cache = ProfileCache()
            cache.save(var, df_profile.to_dict())

            log = SessionLog()
            log.append("profile", f"Profiled {var}. {df_profile.shape[0]:,} rows x {df_profile.shape[1]} cols.")

            return json.dumps(df_profile.to_dict(), indent=2)
        finally:
            kernel.shutdown()

    @server.tool("check")
    async def check_tool(notebook: str, cell: Optional[int] = None) -> str:
        """Check notebook health: state, dependencies, staleness.

        If cell is provided, shows impact of modifying that cell.
        """
        from dasa.notebook.jupyter import JupyterAdapter
        from dasa.analysis.state import StateAnalyzer
        from dasa.analysis.deps import DependencyAnalyzer
        from dasa.session.log import SessionLog

        adapter = JupyterAdapter(notebook)
        state_analysis = StateAnalyzer().analyze(adapter)
        dep_graph = DependencyAnalyzer().build_graph(adapter)

        result = {
            "notebook": notebook,
            "cell_count": len(adapter.cells),
            "state": state_analysis.to_dict(),
            "dependencies": dep_graph.to_dict(),
        }
        if cell is not None:
            result["impact"] = {
                "cell": cell,
                "downstream": dep_graph.get_downstream(cell),
            }

        log = SessionLog()
        issue_count = len(state_analysis.issues)
        log.append("check", f"{'Found ' + str(issue_count) + ' issues' if issue_count else 'Consistent'} in {notebook}")

        return json.dumps(result, indent=2)

    @server.tool("run")
    async def run_tool(notebook: str, cell: Optional[int] = None, all_cells: bool = False) -> str:
        """Execute notebook cells with rich error context.

        Returns output or error with available columns/variables and suggestions.
        """
        from dasa.notebook.jupyter import JupyterAdapter
        from dasa.notebook.kernel import DasaKernelManager
        from dasa.analysis.error_context import build_error_context
        from dasa.session.log import SessionLog
        from dasa.session.state import StateTracker

        adapter = JupyterAdapter(notebook)
        code_cells = adapter.code_cells

        if cell is not None:
            targets = [c for c in code_cells if c.index == cell]
        elif all_cells:
            targets = code_cells
        else:
            targets = code_cells

        kernel = DasaKernelManager()
        log = SessionLog()
        state_tracker = StateTracker()
        results = []

        try:
            kernel.start()
            if cell is not None:
                first_target = cell
                for c in code_cells:
                    if c.index < first_target and c.execution_count is not None:
                        kernel.execute(c.source, timeout=300)

            for target in targets:
                result = kernel.execute(target.source, timeout=300)
                if result.success:
                    state_tracker.update_cell(notebook, target.index, target.source)
                    log.append("run", f"Cell {target.index} executed (success)")
                    results.append({"cell": target.index, "success": True, "stdout": result.stdout})
                else:
                    error_ctx = build_error_context(
                        result.error_type or "", result.error or "",
                        target.source, result.traceback, kernel
                    )
                    log.append("run", f"Cell {target.index} failed: {result.error_type}: {result.error}")
                    results.append({"cell": target.index, "success": False, "error": error_ctx})
        finally:
            kernel.shutdown()

        return json.dumps(results, indent=2)

    @server.tool("context")
    async def context_tool(
        action: str = "read",
        goal: Optional[str] = None,
        status: Optional[str] = None,
        log_msg: Optional[str] = None,
    ) -> str:
        """Read or update project context.

        action="read": Returns project state, data profiles, approaches, recent log.
        action="write": Updates goal, status, or appends to log.
        """
        from dasa.session.context import ContextManager
        from dasa.session.log import SessionLog
        from dasa.session.profiles import ProfileCache

        ctx_mgr = ContextManager()
        session_log = SessionLog()
        profile_cache = ProfileCache()

        if action == "write":
            if goal or status:
                ctx_mgr.ensure_session()
                ctx_mgr.update(goal=goal, status=status)
                if goal:
                    session_log.append("user", f"Goal: {goal}")
                if status:
                    session_log.append("user", f"Status: {status}")
            if log_msg:
                ctx_mgr.ensure_session()
                session_log.append("agent", log_msg)
            return json.dumps({"status": "updated"})

        # Read
        ctx = ctx_mgr.read()
        profiles = {}
        for name in profile_cache.list_profiles():
            profiles[name] = profile_cache.load(name)

        return json.dumps({
            "project": {
                "name": ctx.name,
                "goal": ctx.goal,
                "status": ctx.status,
                "notebook": ctx.notebook,
                "constraints": ctx.constraints,
            },
            "approaches": ctx.approaches,
            "profiles": profiles,
            "recent_log": session_log.read(last_n=20),
        }, indent=2, default=str)

    return server


def run_mcp_server():
    """Entry point for the MCP server."""
    server = create_mcp_server()
    if server is None:
        print("Error: MCP package not installed. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream)

    asyncio.run(main())
