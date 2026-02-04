"""Background async runner for long-running cells."""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from dasa.notebook.jupyter import JupyterAdapter
from dasa.notebook.kernel import KernelManager


def get_jobs_dir() -> Path:
    """Get the jobs directory."""
    jobs_dir = Path.home() / ".dasa" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def update_job_status(job_id: str, updates: dict) -> None:
    """Update job status file."""
    jobs_dir = get_jobs_dir()
    job_file = jobs_dir / f"{job_id}.json"

    if job_file.exists():
        job_data = json.loads(job_file.read_text())
    else:
        job_data = {}

    job_data.update(updates)
    job_file.write_text(json.dumps(job_data, indent=2))


def run_cells(
    notebook: str,
    job_id: str,
    cell: Optional[int],
    from_cell: Optional[int],
    to_cell: Optional[int],
    all_cells: bool,
    stale: bool,
    timeout: int
) -> None:
    """Run cells and track progress."""

    print(f"[{datetime.now().isoformat()}] Starting job {job_id}")
    print(f"Notebook: {notebook}")

    adapter = JupyterAdapter(notebook)
    kernel = KernelManager(adapter.kernel_spec or "python3")

    results = []

    try:
        print("Starting kernel...")
        kernel.start()
        update_job_status(job_id, {"status": "running", "progress": "Kernel started"})

        # Determine which cells to run
        code_cells = adapter.code_cells

        if cell is not None:
            cells_to_run = [c for c in code_cells if c.index == cell]
        elif all_cells:
            cells_to_run = code_cells
        elif from_cell is not None:
            cells_to_run = [c for c in code_cells if c.index >= from_cell]
        elif to_cell is not None:
            cells_to_run = [c for c in code_cells if c.index <= to_cell]
        elif stale:
            cells_to_run = [c for c in code_cells if c.execution_count is None]
        else:
            cells_to_run = []

        total_cells = len(cells_to_run)
        print(f"Running {total_cells} cell(s)")

        for i, cell_obj in enumerate(cells_to_run):
            progress_pct = int((i / total_cells) * 100) if total_cells > 0 else 0
            update_job_status(job_id, {
                "progress": f"{progress_pct}%",
                "current_cell": cell_obj.index,
                "cells_completed": i,
                "cells_total": total_cells
            })

            print(f"\n[{datetime.now().isoformat()}] Running Cell {cell_obj.index} ({i+1}/{total_cells})...")
            print(f"  Preview: {cell_obj.source[:100]}...")

            start = time.time()
            result = kernel.execute(cell_obj.source, timeout=timeout)
            elapsed = time.time() - start

            cell_result = {
                "cell": cell_obj.index,
                "success": result.success,
                "elapsed": elapsed,
                "stdout": result.stdout[:1000] if result.stdout else "",
                "error": result.error
            }
            results.append(cell_result)

            if result.success:
                print(f"  SUCCESS ({elapsed:.2f}s)")
                if result.stdout:
                    print(f"  Output: {result.stdout[:200]}")
            else:
                print(f"  FAILED ({elapsed:.2f}s)")
                print(f"  Error: {result.error_type}: {result.error}")

        # Complete
        success_count = sum(1 for r in results if r["success"])
        update_job_status(job_id, {
            "status": "completed",
            "progress": "100%",
            "completed": datetime.now().isoformat(),
            "results": results,
            "summary": {
                "total": total_cells,
                "succeeded": success_count,
                "failed": total_cells - success_count
            }
        })

        print(f"\n[{datetime.now().isoformat()}] Job completed: {success_count}/{total_cells} cells succeeded")

    except Exception as e:
        print(f"\n[{datetime.now().isoformat()}] Job failed: {e}")
        update_job_status(job_id, {
            "status": "failed",
            "error": str(e),
            "completed": datetime.now().isoformat(),
            "results": results
        })
        raise

    finally:
        print("Shutting down kernel...")
        kernel.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Async cell runner")
    parser.add_argument("--notebook", required=True, help="Path to notebook")
    parser.add_argument("--job-id", required=True, help="Job ID")
    parser.add_argument("--cell", type=int, help="Run specific cell")
    parser.add_argument("--from-cell", type=int, help="Run from cell N")
    parser.add_argument("--to-cell", type=int, help="Run to cell N")
    parser.add_argument("--all", action="store_true", help="Run all cells")
    parser.add_argument("--stale", action="store_true", help="Run stale cells")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds")

    args = parser.parse_args()

    run_cells(
        notebook=args.notebook,
        job_id=args.job_id,
        cell=args.cell,
        from_cell=args.from_cell,
        to_cell=args.to_cell,
        all_cells=args.all,
        stale=args.stale,
        timeout=args.timeout
    )


if __name__ == "__main__":
    main()
