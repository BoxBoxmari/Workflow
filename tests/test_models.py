"""Tests for core.models — data contract construction and serialization."""

import unittest
from core.models import (
    IngestResult,
    ProviderResponse,
    RunContext,
    StepDef,
    StepMetrics,
    StepResult,
    WorkflowDef,
    InputPortDef,
    OutputPortDef,
    SourceRef,
)


class TestStepDef(unittest.TestCase):
    def test_defaults(self):
        s = StepDef(id="s1", name="step1", model="m", prompt_version="1")
        self.assertEqual(s.input_mapping, "input")
        self.assertEqual(s.output_mapping, "output")
        self.assertTrue(s.enabled)

    def test_v3_schema_fields(self):
        s = StepDef(
            id="s1",
            name="step1",
            model="m",
            prompt_version="1",
            execution_mode="graph",
            inputs=[InputPortDef(name="in1")],
            outputs=[OutputPortDef(name="out1")],
        )
        d = s.to_dict()
        s2 = StepDef.from_dict(d)
        self.assertEqual(s2.execution_mode, "graph")
        self.assertEqual(len(s2.inputs), 1)
        self.assertEqual(s2.inputs[0].name, "in1")
        self.assertEqual(len(s2.outputs), 1)
        self.assertEqual(s2.outputs[0].name, "out1")

    def test_from_dict_infers_legacy_for_mapping_only_steps(self):
        s = StepDef.from_dict(
            {
                "id": "s1",
                "name": "step1",
                "model": "m",
                "prompt_version": "1",
                "input_mapping": "input",
                "output_mapping": "output",
            }
        )
        self.assertEqual(s.execution_mode, "legacy")

    def test_from_dict_defaults_to_legacy_without_graph_payload(self):
        s = StepDef.from_dict(
            {
                "id": "s1",
                "name": "step1",
                "model": "m",
                "prompt_version": "1",
            }
        )
        self.assertEqual(s.execution_mode, "legacy")


class TestPortDefs(unittest.TestCase):
    def test_input_port_roundtrip(self):
        p = InputPortDef(name="in1", sources=[SourceRef(step_id="s1", port="out1")])
        d = p.to_dict()
        p2 = InputPortDef.from_dict(d)
        self.assertEqual(p2.name, "in1")
        self.assertEqual(len(p2.sources), 1)
        self.assertEqual(p2.sources[0].step_id, "s1")

    def test_output_port_roundtrip(self):
        p = OutputPortDef(name="out1", exposed=False)
        d = p.to_dict()
        p2 = OutputPortDef.from_dict(d)
        self.assertEqual(p2.name, "out1")
        self.assertFalse(p2.exposed)


class TestWorkflowDef(unittest.TestCase):
    def test_to_dict_from_dict_roundtrip(self):
        wf = WorkflowDef(
            id="wf1",
            name="Test WF",
            description="desc",
            steps=[StepDef(id="s1", name="step1", model="m", prompt_version="1")],
        )
        d = wf.to_dict()
        wf2 = WorkflowDef.from_dict(d)
        self.assertEqual(wf2.id, "wf1")
        self.assertEqual(wf2.name, "Test WF")
        self.assertEqual(len(wf2.steps), 1)
        self.assertEqual(wf2.steps[0].id, "s1")


class TestProviderResponse(unittest.TestCase):
    def test_ok_success(self):
        r = ProviderResponse(content="hi", status_code=200)
        self.assertTrue(r.ok)

    def test_ok_error(self):
        r = ProviderResponse(status_code=400, error="bad")
        self.assertFalse(r.ok)


class TestStepMetrics(unittest.TestCase):
    def test_roundtrip(self):
        m = StepMetrics(latency_ms=123.4, model="gpt-4o", prompt_version="1")
        d = m.to_dict()
        m2 = StepMetrics.from_dict(d)
        self.assertAlmostEqual(m2.latency_ms, 123.4)
        self.assertEqual(m2.model, "gpt-4o")


class TestStepResult(unittest.TestCase):
    def test_roundtrip(self):
        sr = StepResult(
            step_id="s1",
            step_name="step1",
            input_text="hello",
            output_text="world",
            status="success",
            metrics=StepMetrics(latency_ms=100, model="test"),
        )
        d = sr.to_dict()
        sr2 = StepResult.from_dict(d)
        self.assertEqual(sr2.step_id, "s1")
        self.assertEqual(sr2.output_text, "world")
        self.assertAlmostEqual(sr2.metrics.latency_ms, 100)

    def test_from_dict_does_not_mutate_input(self):
        """H2 regression: from_dict() must not modify the input dictionary."""
        sr = StepResult(
            step_id="s2",
            output_text="result",
            status="success",
            metrics=StepMetrics(latency_ms=50, model="gpt-4o"),
        )
        d = sr.to_dict()
        metrics_before = d.get("metrics")  # capture before
        StepResult.from_dict(d)
        # dict must still have "metrics" key with same value
        self.assertIn(
            "metrics", d, "from_dict() removed 'metrics' key (mutation detected)"
        )
        self.assertEqual(d.get("metrics"), metrics_before)


class TestRunContext(unittest.TestCase):
    def test_run_id_generated(self):
        rc = RunContext()
        self.assertRegex(rc.run_id, r"\d{8}_\d{6}_[a-f0-9]{8}")

    def test_roundtrip(self):
        rc = RunContext(workflow_id="w1", workflow_name="test", status="success")
        d = rc.to_dict()
        rc2 = RunContext.from_dict(d)
        self.assertEqual(rc2.workflow_id, "w1")
        self.assertEqual(rc2.status, "success")


class TestIngestResult(unittest.TestCase):
    def test_ok(self):
        r = IngestResult(content="data")
        self.assertTrue(r.ok)

    def test_error(self):
        r = IngestResult(error="fail")
        self.assertFalse(r.ok)


if __name__ == "__main__":
    unittest.main()
