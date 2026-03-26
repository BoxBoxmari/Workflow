"""Tests for core.storage — local file persistence."""

import tempfile
import unittest
from pathlib import Path

from core.models import RunContext, StepMetrics, StepResult
from core.storage import StorageManager


class TestStorageManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.storage = StorageManager(Path(self.tmpdir))

    def test_create_run_creates_dirs(self):
        rc = RunContext(run_id="test_run_001", workflow_id="wf1", workflow_name="Test")
        path = self.storage.create_run(rc)
        self.assertTrue(path.is_dir())
        self.assertTrue((path / "steps").is_dir())
        self.assertTrue((path / "artifacts").is_dir())
        self.assertTrue((path / "run.json").is_file())

    def test_save_load_run_roundtrip(self):
        rc = RunContext(
            run_id="test_run_002",
            workflow_id="wf1",
            workflow_name="Test",
            status="success",
        )
        self.storage.create_run(rc)
        loaded = self.storage.load_run("test_run_002")
        self.assertEqual(loaded.workflow_name, "Test")
        self.assertEqual(loaded.status, "success")

    def test_save_load_step(self):
        rc = RunContext(run_id="test_run_003")
        self.storage.create_run(rc)

        sr = StepResult(
            step_id="s1",
            step_name="step1",
            output_text="result",
            status="success",
            metrics=StepMetrics(latency_ms=42.0, model="test"),
        )
        self.storage.save_step("test_run_003", sr)

        files = self.storage.list_step_files("test_run_003")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "step_01.json")

        loaded = self.storage.load_step("test_run_003", "step_01.json")
        self.assertEqual(loaded.step_id, "s1")
        self.assertEqual(loaded.output_text, "result")

    def test_save_step_uses_counter_and_increments(self):
        rc = RunContext(run_id="test_run_003b")
        self.storage.create_run(rc)

        sr1 = StepResult(step_id="s1", step_name="step1", status="success")
        sr2 = StepResult(step_id="s2", step_name="step2", status="success")
        self.storage.save_step("test_run_003b", sr1)
        self.storage.save_step("test_run_003b", sr2)

        files = self.storage.list_step_files("test_run_003b")
        self.assertEqual(files, ["step_01.json", "step_02.json"])

        counter_path = self.storage._steps_dir("test_run_003b") / ".step_counter"
        self.assertTrue(counter_path.is_file())
        self.assertEqual(counter_path.read_text(encoding="utf-8").strip(), "2")

    def test_append_load_events(self):
        rc = RunContext(run_id="test_run_004")
        self.storage.create_run(rc)

        self.storage.append_event("test_run_004", {"type": "start", "msg": "hello"})
        self.storage.append_event("test_run_004", {"type": "end", "msg": "bye"})

        events = self.storage.load_events("test_run_004")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["type"], "start")
        self.assertEqual(events[1]["type"], "end")

    def test_index_update_and_list(self):
        rc1 = RunContext(
            run_id="run_a", workflow_id="wf1", workflow_name="WF A", status="success"
        )
        rc2 = RunContext(
            run_id="run_b", workflow_id="wf2", workflow_name="WF B", status="error"
        )

        self.storage.create_run(rc1)
        self.storage.update_index(rc1)
        self.storage.create_run(rc2)
        self.storage.update_index(rc2)
        # update_index() is async — wait for background queue to drain before reading
        self.storage._write_queue.flush()

        runs = self.storage.list_runs()
        self.assertEqual(len(runs), 2)
        ids = [r.run_id for r in runs]
        self.assertIn("run_a", ids)
        self.assertIn("run_b", ids)

    def test_index_update_existing(self):
        rc = RunContext(run_id="run_c", status="running")
        self.storage.create_run(rc)
        self.storage.update_index(rc)
        self.storage._write_queue.flush()  # wait for first write to land

        rc.status = "success"
        self.storage.update_index(rc)
        self.storage._write_queue.flush()  # wait for update write to land

        runs = self.storage.list_runs()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].status, "success")

    def test_index_update_existing_preserves_ordering(self):
        rc1 = RunContext(run_id="run_1", workflow_id="wf1", workflow_name="WF 1")
        rc2 = RunContext(run_id="run_2", workflow_id="wf2", workflow_name="WF 2")
        rc3 = RunContext(run_id="run_3", workflow_id="wf3", workflow_name="WF 3")

        self.storage.create_run(rc1)
        self.storage.update_index(rc1)
        self.storage.create_run(rc2)
        self.storage.update_index(rc2)
        self.storage.create_run(rc3)
        self.storage.update_index(rc3)
        self.storage._write_queue.flush()

        before = [r.run_id for r in self.storage.list_runs()]
        self.assertEqual(before, ["run_1", "run_2", "run_3"])

        # Update an existing run; it should NOT move to the end.
        rc2.status = "success"
        self.storage.update_index(rc2)
        self.storage._write_queue.flush()

        after = [r.run_id for r in self.storage.list_runs()]
        self.assertEqual(after, ["run_1", "run_2", "run_3"])
        runs = self.storage.list_runs()
        self.assertEqual([r.status for r in runs if r.run_id == "run_2"][0], "success")

    def test_compact_index_dedupes_latest_status_and_preserves_ordering(self):
        rc1 = RunContext(run_id="run_x", status="running")
        rc2 = RunContext(run_id="run_y", status="running")

        self.storage.create_run(rc1)
        self.storage.update_index(rc1)
        self.storage.create_run(rc2)
        self.storage.update_index(rc2)
        self.storage._write_queue.flush()

        # Append a few updates (duplicates in index.csv)
        rc1.status = "success"
        self.storage.update_index(rc1)
        rc2.status = "error"
        self.storage.update_index(rc2)
        self.storage._write_queue.flush()

        # Compact should rewrite to 1 row per run_id with latest status,
        # keeping ordering by first appearance (run_x then run_y).
        self.storage.compact_index()
        runs = self.storage.list_runs()
        self.assertEqual([r.run_id for r in runs], ["run_x", "run_y"])
        statuses = {r.run_id: r.status for r in runs}
        self.assertEqual(statuses["run_x"], "success")
        self.assertEqual(statuses["run_y"], "error")

    def test_save_artifact(self):
        rc = RunContext(run_id="test_run_005")
        self.storage.create_run(rc)

        path = self.storage.save_artifact("test_run_005", "test.txt", "hello world")
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_text(), "hello world")

        artifacts = self.storage.list_artifacts("test_run_005")
        self.assertEqual(artifacts, ["test.txt"])

    def test_load_all_steps_legacy(self):
        rc = RunContext(run_id="test_run_006")
        self.storage.create_run(rc)

        for i in range(3):
            sr = StepResult(step_id=f"s{i}", step_name=f"step{i}", status="success")
            self.storage.save_step("test_run_006", sr)

        all_steps = self.storage.load_all_steps("test_run_006")
        self.assertEqual(len(all_steps), 3)
        self.assertEqual(all_steps[0].step_id, "s0")
        self.assertEqual(all_steps[2].step_id, "s2")

    def test_load_all_steps_graph(self):
        rc = RunContext(run_id="test_run_007", engine_type="graph")
        self.storage.create_run(rc)

        for i in range(3):
            # Give them specific timestamp ordering to test sort
            sr = StepResult(
                step_id=f"node{i}",
                step_name=f"step{i}",
                status="success",
                metrics=StepMetrics(timestamp=f"2026-01-01T00:00:0{i}Z"),
            )
            self.storage.save_node("test_run_007", sr.step_id, sr)

        all_steps = self.storage.load_all_steps("test_run_007")
        self.assertEqual(len(all_steps), 3)
        self.assertEqual(all_steps[0].step_id, "node0")
        self.assertEqual(all_steps[2].step_id, "node2")

    def test_save_load_port(self):
        rc = RunContext(run_id="test_run_008")
        self.storage.create_run(rc)

        path = self.storage.save_port("test_run_008", "stepA", "out1", "raw payload")
        self.assertTrue(path.is_file())
        self.assertEqual(path.name, "stepA__out1.json")

        content = self.storage.load_port("test_run_008", "stepA", "out1")
        self.assertEqual(content, "raw payload")

        # Missing port check
        missing = self.storage.load_port("test_run_008", "stepA", "unknown")
        self.assertEqual(missing, "")


if __name__ == "__main__":
    unittest.main()
