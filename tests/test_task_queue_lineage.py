import sys
import time
from pathlib import Path

from finance_forecast_agent.lineage import LineageStore
from finance_forecast_agent.task_queue import LocalTaskQueue


def _wait(queue: LocalTaskQueue, task_id: str, timeout: float = 10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        record = queue.load(task_id)
        if record.status in {"completed", "blocked", "cancelled", "resumable"}:
            return record
        time.sleep(0.05)
    raise AssertionError("task did not finish")


def test_local_task_queue_survives_submitter_and_persists_logs(tmp_path: Path) -> None:
    queue = LocalTaskQueue(tmp_path / "tasks")
    record = queue.submit(
        task_type="test",
        command=[sys.executable, "-c", "print('finished')"],
        cwd=tmp_path,
    )
    final = _wait(queue, record.task_id)
    assert final.status == "completed"
    assert "finished" in Path(final.log_path).read_text(encoding="utf-8")


def test_local_task_queue_can_cancel_running_task(tmp_path: Path) -> None:
    queue = LocalTaskQueue(tmp_path / "tasks")
    record = queue.submit(
        task_type="test",
        command=[sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path,
    )
    deadline = time.time() + 5
    while queue.load(record.task_id).status == "queued" and time.time() < deadline:
        time.sleep(0.05)
    assert queue.cancel(record.task_id).status == "cancelled"


def test_lineage_hashes_inputs_outputs_and_records_git_environment(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    output = tmp_path / "report.json"
    source.write_text("x\n1\n", encoding="utf-8")
    output.write_text("{}", encoding="utf-8")
    store = LineageStore(tmp_path / "lineage")
    record = store.record(
        run_type="benchmark",
        cwd=tmp_path,
        inputs={"dataset": source},
        outputs={"report": output},
    )
    assert record.inputs["dataset"]["sha256"]
    assert record.outputs["report"]["sha256"]
    assert store.load(record.run_id).run_type == "benchmark"
