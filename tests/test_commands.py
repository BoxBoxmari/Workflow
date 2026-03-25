"""Tests for core.commands — undo/redo command pattern."""

import unittest

from core.commands import (
    AddStepCommand,
    CommandStack,
    DeleteStepCommand,
    DuplicateStepCommand,
    UpdateStepFieldCommand,
    AddInputPortCommand,
    RemoveInputPortCommand,
    AddOutputPortCommand,
    UpdatePortConfigCommand,
)
from core.models import StepDef, WorkflowDef, InputPortDef, OutputPortDef


def _make_step(step_id: str) -> StepDef:
    return StepDef(
        id=step_id, name=f"name_{step_id}", model="gpt-4o", prompt_version="1"
    )


def _make_workflow(*step_ids) -> WorkflowDef:
    return WorkflowDef(id="wf1", name="WF", steps=[_make_step(s) for s in step_ids])


class TestAddStepCommand(unittest.TestCase):
    def setUp(self):
        self.wf = _make_workflow("A", "B")
        self.new_step = _make_step("C")

    def test_execute_appends(self):
        cmd = AddStepCommand("add", self.wf, self.new_step, index=2)
        cmd.execute()
        self.assertEqual(len(self.wf.steps), 3)
        self.assertEqual(self.wf.steps[2].id, "C")

    def test_execute_inserts_at_index(self):
        cmd = AddStepCommand("add", self.wf, self.new_step, index=1)
        cmd.execute()
        self.assertEqual(self.wf.steps[1].id, "C")

    def test_undo_removes_step(self):
        cmd = AddStepCommand("add", self.wf, self.new_step, index=2)
        cmd.execute()
        cmd.undo()
        self.assertEqual(len(self.wf.steps), 2)
        self.assertNotIn("C", [s.id for s in self.wf.steps])


class TestDeleteStepCommand(unittest.TestCase):
    def setUp(self):
        self.wf = _make_workflow("A", "B", "C")

    def test_execute_removes(self):
        cmd = DeleteStepCommand("del", self.wf, "B")
        cmd.execute()
        self.assertEqual([s.id for s in self.wf.steps], ["A", "C"])

    def test_undo_restores(self):
        cmd = DeleteStepCommand("del", self.wf, "B")
        cmd.execute()
        cmd.undo()
        ids = [s.id for s in self.wf.steps]
        self.assertIn("B", ids)
        self.assertEqual(ids.index("B"), 1)

    def test_delete_nonexistent_does_not_raise(self):
        cmd = DeleteStepCommand("del", self.wf, "X")
        cmd.execute()  # Should not raise
        self.assertEqual(len(self.wf.steps), 3)


class TestUpdateStepFieldCommand(unittest.TestCase):
    def setUp(self):
        self.step = _make_step("A")
        self.wf = WorkflowDef(id="wf1", name="WF", steps=[self.step])

    def test_execute_updates_field(self):
        cmd = UpdateStepFieldCommand("upd", self.step, "model", "gpt-3.5")
        cmd.execute()
        self.assertEqual(self.step.model, "gpt-3.5")

    def test_undo_restores_field(self):
        cmd = UpdateStepFieldCommand("upd", self.step, "model", "gpt-3.5")
        cmd.execute()
        cmd.undo()
        self.assertEqual(self.step.model, "gpt-4o")

    def test_update_title(self):
        cmd = UpdateStepFieldCommand("upd", self.step, "title", "My Title")
        cmd.execute()
        self.assertEqual(self.step.title, "My Title")
        cmd.undo()
        self.assertEqual(self.step.title, "")


class TestDuplicateStepCommand(unittest.TestCase):
    def setUp(self):
        self.wf = _make_workflow("A", "B")

    def test_execute_creates_copy(self):
        cmd = DuplicateStepCommand("dup", self.wf, "A")
        cmd.execute()
        self.assertEqual(len(self.wf.steps), 3)
        ids = [s.id for s in self.wf.steps]
        self.assertNotEqual(ids[0], ids[1])  # different id

    def test_undo_removes_copy(self):
        cmd = DuplicateStepCommand("dup", self.wf, "A")
        cmd.execute()
        new_id = cmd.new_step.id
        cmd.undo()
        ids = [s.id for s in self.wf.steps]
        self.assertNotIn(new_id, ids)
        self.assertEqual(len(self.wf.steps), 2)

    def test_dup_nonexistent_is_noop(self):
        cmd = DuplicateStepCommand("dup", self.wf, "MISSING")
        cmd.execute()
        self.assertEqual(len(self.wf.steps), 2)


class TestPortCommands(unittest.TestCase):
    def setUp(self):
        self.step = _make_step("A")
        self.port1 = InputPortDef(name="in1")
        self.step.inputs = [self.port1]

    def test_add_input_port(self):
        new_port = InputPortDef(name="in2")
        cmd = AddInputPortCommand("add_in", self.step, new_port)
        cmd.execute()
        self.assertEqual(len(self.step.inputs), 2)
        self.assertEqual(self.step.inputs[1].name, "in2")
        cmd.undo()
        self.assertEqual(len(self.step.inputs), 1)

    def test_remove_input_port(self):
        cmd = RemoveInputPortCommand("rm_in", self.step, "in1")
        cmd.execute()
        self.assertEqual(len(self.step.inputs), 0)
        cmd.undo()
        self.assertEqual(len(self.step.inputs), 1)
        self.assertEqual(self.step.inputs[0].name, "in1")

    def test_add_output_port(self):
        new_port = OutputPortDef(name="out1")
        cmd = AddOutputPortCommand("add_out", self.step, new_port)
        cmd.execute()
        self.assertEqual(len(self.step.outputs), 1)
        self.assertEqual(self.step.outputs[0].name, "out1")
        cmd.undo()
        self.assertEqual(len(self.step.outputs), 0)

    def test_update_port_config(self):
        cmd = UpdatePortConfigCommand(
            "upd_port", self.step, "input", "in1", "required", False
        )
        cmd.execute()
        self.assertFalse(self.step.inputs[0].required)
        cmd.undo()
        self.assertTrue(self.step.inputs[0].required)


class TestCommandStack(unittest.TestCase):
    def setUp(self):
        self.wf = _make_workflow("A", "B")
        self.stack = CommandStack()

    def test_undo_after_execute(self):
        cmd = AddStepCommand("add", self.wf, _make_step("C"), index=2)
        self.stack.execute(cmd)
        self.assertEqual(len(self.wf.steps), 3)
        self.stack.undo()
        self.assertEqual(len(self.wf.steps), 2)

    def test_redo_after_undo(self):
        cmd = AddStepCommand("add", self.wf, _make_step("C"), index=2)
        self.stack.execute(cmd)
        self.stack.undo()
        self.stack.redo()
        self.assertEqual(len(self.wf.steps), 3)

    def test_undo_empty_stack_returns_none(self):
        result = self.stack.undo()
        self.assertIsNone(result)

    def test_redo_empty_stack_returns_none(self):
        result = self.stack.redo()
        self.assertIsNone(result)

    def test_new_command_clears_redo(self):
        cmd1 = AddStepCommand("add", self.wf, _make_step("C"), index=2)
        self.stack.execute(cmd1)
        self.stack.undo()
        # Execute new command — redo stack should clear
        cmd2 = AddStepCommand("add", self.wf, _make_step("D"), index=2)
        self.stack.execute(cmd2)
        result = self.stack.redo()
        self.assertIsNone(result)

    def test_clear(self):
        cmd = AddStepCommand("add", self.wf, _make_step("C"), index=2)
        self.stack.execute(cmd)
        self.stack.clear()
        self.assertIsNone(self.stack.undo())

    def test_can_undo_can_redo(self):
        self.assertFalse(self.stack.can_undo())
        cmd = AddStepCommand("add", self.wf, _make_step("C"), index=2)
        self.stack.execute(cmd)
        self.assertTrue(self.stack.can_undo())
        self.assertFalse(self.stack.can_redo())
        self.stack.undo()
        self.assertTrue(self.stack.can_redo())


if __name__ == "__main__":
    unittest.main()
