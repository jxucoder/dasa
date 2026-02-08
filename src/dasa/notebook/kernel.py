"""Jupyter kernel lifecycle and execution."""

import time
from dataclasses import dataclass, field
from typing import Optional, Any

from jupyter_client.manager import KernelManager as JupyterKM


@dataclass
class ExecutionResult:
    """Result of executing code in a kernel."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    traceback: list[str] = field(default_factory=list)
    execution_time: float = 0.0


class DasaKernelManager:
    """Start, execute, restart, interrupt Jupyter kernels."""

    def __init__(self):
        self._km: Optional[JupyterKM] = None
        self._kc = None

    def start(self, kernel_name: str = "python3") -> None:
        """Start a new kernel."""
        self._km = JupyterKM(kernel_name=kernel_name)
        self._km.start_kernel()
        self._kc = self._km.client()
        self._kc.start_channels()
        self._kc.wait_for_ready(timeout=30)

    def shutdown(self) -> None:
        """Shut down the kernel."""
        if self._kc:
            self._kc.stop_channels()
        if self._km:
            self._km.shutdown_kernel(now=True)
        self._kc = None
        self._km = None

    def restart(self) -> None:
        """Restart the kernel."""
        if self._km:
            self._km.restart_kernel()
            if self._kc:
                self._kc.wait_for_ready(timeout=30)

    def interrupt(self) -> None:
        """Interrupt the kernel."""
        if self._km:
            self._km.interrupt_kernel()

    def execute(self, code: str, timeout: int = 300) -> ExecutionResult:
        """Execute code in the kernel and return result."""
        if not self._kc:
            raise RuntimeError("Kernel not started. Call start() first.")

        start_time = time.time()
        msg_id = self._kc.execute(code)

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        result_value = None
        error = None
        error_type = None
        tb: list[str] = []

        while True:
            try:
                msg = self._kc.get_iopub_msg(timeout=timeout)
            except Exception:
                return ExecutionResult(
                    success=False,
                    error="Timeout waiting for kernel response",
                    execution_time=time.time() - start_time,
                )

            if msg["parent_header"].get("msg_id") != msg_id:
                continue

            msg_type = msg["msg_type"]
            content = msg["content"]

            if msg_type == "stream":
                if content["name"] == "stdout":
                    stdout_parts.append(content["text"])
                elif content["name"] == "stderr":
                    stderr_parts.append(content["text"])
            elif msg_type in ("execute_result", "display_data"):
                result_value = content.get("data", {}).get("text/plain", "")
            elif msg_type == "error":
                error_type = content.get("ename", "")
                error = content.get("evalue", "")
                tb = content.get("traceback", [])
            elif msg_type == "status" and content.get("execution_state") == "idle":
                break

        elapsed = time.time() - start_time
        success = error is None

        return ExecutionResult(
            success=success,
            stdout="".join(stdout_parts),
            stderr="".join(stderr_parts),
            result=result_value,
            error=error,
            error_type=error_type,
            traceback=tb,
            execution_time=elapsed,
        )

    @property
    def is_alive(self) -> bool:
        """Check if the kernel is alive."""
        return self._km is not None and self._km.is_alive()
