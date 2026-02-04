"""Jupyter kernel management."""

import queue
from dataclasses import dataclass, field
from typing import Any, Optional

from jupyter_client import KernelManager as JupyterKernelManager


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    stdout: str
    stderr: str
    result: Optional[Any]
    error: Optional[str] = None
    error_type: Optional[str] = None
    traceback: list[str] = field(default_factory=list)
    execution_time: float = 0.0


class KernelManager:
    """Manages Jupyter kernel for code execution."""

    def __init__(self, kernel_name: str = "python3"):
        self.kernel_name = kernel_name
        self._km: Optional[JupyterKernelManager] = None
        self._kc: Any = None  # KernelClient

    @property
    def is_alive(self) -> bool:
        """Check if kernel is running."""
        return self._km is not None and self._km.is_alive()

    def start(self) -> None:
        """Start the kernel."""
        if self.is_alive:
            return

        self._km = JupyterKernelManager(kernel_name=self.kernel_name)
        self._km.start_kernel()
        self._kc = self._km.client()
        self._kc.start_channels()
        self._kc.wait_for_ready(timeout=60)

    def shutdown(self) -> None:
        """Shutdown the kernel."""
        if self._kc:
            self._kc.stop_channels()
        if self._km:
            self._km.shutdown_kernel(now=True)
        self._km = None
        self._kc = None

    def restart(self) -> None:
        """Restart the kernel (clears all state)."""
        if self._km:
            self._km.restart_kernel(now=True)
            self._kc.wait_for_ready(timeout=60)
        else:
            self.start()

    def interrupt(self) -> None:
        """Interrupt current execution."""
        if self._km:
            self._km.interrupt_kernel()

    def execute(self, code: str, timeout: int = 300) -> ExecutionResult:
        """Execute code and return result."""
        if not self._kc:
            self.start()

        msg_id = self._kc.execute(code)

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        result = None
        error = None
        error_type = None
        traceback: list[str] = []

        while True:
            try:
                msg = self._kc.get_iopub_msg(timeout=timeout)
            except queue.Empty:
                return ExecutionResult(
                    success=False,
                    stdout="".join(stdout_parts),
                    stderr="".join(stderr_parts),
                    result=None,
                    error="Execution timed out",
                    error_type="TimeoutError"
                )

            # Skip messages from other executions
            if msg['parent_header'].get('msg_id') != msg_id:
                continue

            msg_type = msg['msg_type']
            content = msg['content']

            if msg_type == 'stream':
                if content['name'] == 'stdout':
                    stdout_parts.append(content['text'])
                elif content['name'] == 'stderr':
                    stderr_parts.append(content['text'])

            elif msg_type == 'execute_result':
                result = content.get('data', {})

            elif msg_type == 'display_data':
                # Could capture displays here
                if result is None:
                    result = content.get('data', {})

            elif msg_type == 'error':
                error_type = content['ename']
                error = content['evalue']
                traceback = content['traceback']

            elif msg_type == 'status':
                if content['execution_state'] == 'idle':
                    break

        return ExecutionResult(
            success=error is None,
            stdout="".join(stdout_parts),
            stderr="".join(stderr_parts),
            result=result,
            error=error,
            error_type=error_type,
            traceback=traceback
        )

    def get_variable(self, var_name: str) -> str:
        """Get a variable's value from the kernel."""
        code = f"__dasa_result__ = {var_name}"
        result = self.execute(code)

        if not result.success:
            raise NameError(f"Variable '{var_name}' not found: {result.error}")

        # Get the value as JSON for transfer
        code = """
import json
try:
    print(json.dumps(__dasa_result__, default=str))
except:
    print(repr(__dasa_result__))
"""
        result = self.execute(code)
        return result.stdout.strip()

    def get_variables(self) -> dict[str, str]:
        """Get all user-defined variables from the kernel."""
        code = """
import json
_dasa_vars = {}
for _name in dir():
    if not _name.startswith('_'):
        try:
            _val = eval(_name)
            _dasa_vars[_name] = type(_val).__name__
        except:
            pass
print(json.dumps(_dasa_vars))
"""
        result = self.execute(code)
        if result.success and result.stdout:
            import json
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {}
        return {}

    def __enter__(self) -> "KernelManager":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.shutdown()
