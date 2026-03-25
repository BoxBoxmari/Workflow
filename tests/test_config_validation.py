import unittest
from core.models import WorkflowDef, StepDef, InputPortDef, OutputPortDef, SourceRef
from core.config_validation import validate_workflow, validate_prompt


class TestConfigValidation(unittest.TestCase):
    def setUp(self):
        self.wf1 = WorkflowDef(
            id="v_wf1",
            name="Test WF 1",
            steps=[
                StepDef(
                    id="s1",
                    name="analyze",
                    model="gpt-4o",
                    prompt_version="1",
                    input_mapping="input",
                    output_mapping="analysis",
                ),
            ],
        )

        self.prompts = {"analyze": ["1", "2"]}

    def test_validate_workflow_success(self):
        issues = validate_workflow(self.wf1, [self.wf1], self.prompts)
        self.assertEqual(len(issues), 0)

    def test_validate_workflow_missing_step(self):
        wf = WorkflowDef(id="err1", name="empty", steps=[])
        issues = validate_workflow(wf, [], self.prompts)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].message, "Workflow must contain at least one step.")

    def test_validate_workflow_duplicate_id(self):
        wf2 = WorkflowDef(id="v_wf1", name="Dupe", steps=[self.wf1.steps[0]])
        issues = validate_workflow(wf2, [self.wf1, wf2], self.prompts)
        self.assertTrue(any("Duplicate workflow ID" in i.message for i in issues))

    def test_validate_workflow_duplicate_step_id(self):
        self.wf1.steps.append(
            StepDef(
                id="s1",
                name="analyze",
                model="gpt-4o",
                prompt_version="1",
                input_mapping="analysis",
            )
        )
        issues = validate_workflow(self.wf1, [self.wf1], self.prompts)
        self.assertTrue(any("Duplicate step ID 's1'" in i.message for i in issues))

    def test_validate_workflow_missing_prompt_version(self):
        self.wf1.steps[0].prompt_version = "99"
        issues = validate_workflow(self.wf1, [self.wf1], self.prompts)
        self.assertTrue(
            any("Prompt version 'v99' does not exist" in i.message for i in issues)
        )

    def test_validate_prompt_success(self):
        issues = validate_prompt("[system]\nHello\n[user]\nAnalyze $input")
        self.assertEqual(len(issues), 0)

    def test_validate_prompt_no_roles(self):
        issues = validate_prompt("This is just raw text without roles.")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].level, "warning")
        self.assertTrue("No [system] or [user] role" in issues[0].message)

    def test_validate_prompt_stray_dollars(self):
        issues = validate_prompt(
            "[user]\nHere is a price $ 5 and another variable $input"
        )
        warnings = [i for i in issues if i.level == "warning"]
        self.assertTrue(any("unescaped '$'" in w.message for w in warnings))

    def test_validate_workflow_empty_model(self):
        """Workflow with empty model field should fail validation."""
        wf = WorkflowDef(
            id="test_empty_model",
            name="Test",
            steps=[
                StepDef(
                    id="step1",
                    name="analyze",
                    model="",  # Empty model
                    prompt_version="1",
                    input_mapping="input",
                )
            ],
        )
        issues = validate_workflow(wf, [wf], {"analyze": ["1"]})
        model_errors = [
            i
            for i in issues
            if "Model field is empty" in i.message and i.level == "error"
        ]
        self.assertEqual(len(model_errors), 1)

    def test_validate_workflow_empty_prompt_version(self):
        """Workflow with empty prompt_version should fail validation."""
        wf = WorkflowDef(
            id="test_empty_version",
            name="Test",
            steps=[
                StepDef(
                    id="step1",
                    name="analyze",
                    model="gpt-4o",
                    prompt_version="",  # Empty version
                    input_mapping="input",
                )
            ],
        )
        issues = validate_workflow(wf, [wf], {"analyze": ["1"]})
        version_errors = [
            i
            for i in issues
            if "Prompt version is empty" in i.message and i.level == "error"
        ]
        self.assertEqual(len(version_errors), 1)

    def test_validate_workflow_missing_step_id(self):
        wf = WorkflowDef(
            id="test_missing_id",
            name="Test",
            steps=[StepDef(id="", name="analyze", model="m", prompt_version="1")],
        )
        issues = validate_workflow(wf, [wf], {"analyze": ["1"]})
        self.assertTrue(any("Missing step ID" in i.message for i in issues))

    def test_validate_workflow_invalid_input_mapping(self):
        wf = WorkflowDef(
            id="test_invalid_mapping",
            name="Test",
            steps=[
                StepDef(
                    id="s1",
                    name="analyze",
                    model="m",
                    prompt_version="1",
                    input_mapping="missing_var",
                    execution_mode="legacy",
                )
            ],
        )
        issues = validate_workflow(wf, [wf], {"analyze": ["1"]})
        self.assertTrue(
            any("is not produced by any prior step" in i.message for i in issues)
        )

    def test_validate_workflow_model_not_in_available(self):
        wf = WorkflowDef(
            id="test_invalid_model",
            name="Test",
            steps=[StepDef(id="s1", name="analyze", model="gpt-9", prompt_version="1")],
        )
        issues = validate_workflow(
            wf, [wf], {"analyze": ["1"]}, available_models=["gpt-3.5", "gpt-4o"]
        )
        self.assertTrue(
            any("not in the valid models catalog" in i.message for i in issues)
        )

    def test_validate_workflow_no_prompts_exist_for_step(self):
        wf = WorkflowDef(
            id="test_no_prompts",
            name="Test",
            steps=[
                StepDef(id="s1", name="unknown_step", model="m", prompt_version="1")
            ],
        )
        issues = validate_workflow(wf, [wf], {"analyze": ["1"]})
        self.assertTrue(
            any("No prompts exist for step name" in i.message for i in issues)
        )

    def test_validate_workflow_depends_on_missing_step(self):
        wf = WorkflowDef(
            id="test_missing_dep",
            name="Test",
            steps=[
                StepDef(
                    id="s1",
                    name="analyze",
                    model="m",
                    prompt_version="1",
                    depends_on=["s2"],
                    execution_mode="legacy",
                )
            ],
        )
        issues = validate_workflow(wf, [wf], {"analyze": ["1"]})
        self.assertTrue(
            any("depends_on 's2' which does not exist" in i.message for i in issues)
        )

    def test_validate_workflow_dependency_cycle(self):
        wf = WorkflowDef(
            id="test_dep_cycle",
            name="Test",
            steps=[
                StepDef(
                    id="s1",
                    name="analyze",
                    model="m",
                    prompt_version="1",
                    depends_on=["s2"],
                    execution_mode="legacy",
                ),
                StepDef(
                    id="s2",
                    name="analyze",
                    model="m",
                    prompt_version="1",
                    depends_on=["s1"],
                    execution_mode="legacy",
                ),
            ],
        )
        issues = validate_workflow(wf, [wf], {"analyze": ["1"]})
        self.assertTrue(any("Circular dependency" in i.message for i in issues))

    def test_validate_graph_duplicate_input_port(self):
        wf = WorkflowDef(
            id="g1",
            name="G1",
            steps=[
                StepDef(
                    id="s1",
                    name="s1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(name="in1", sources=[]),
                        InputPortDef(name="in1", sources=[]),
                    ],
                )
            ],
        )
        issues = validate_workflow(wf, [wf], {"s1": ["1"]})
        self.assertTrue(
            any("Duplicate input port name 'in1'" in i.message for i in issues)
        )

    def test_validate_graph_invalid_join_strategy(self):
        wf = WorkflowDef(
            id="g1",
            name="G1",
            steps=[
                StepDef(
                    id="s1",
                    name="s1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="in1", join_strategy="invalid_strat", sources=[]
                        )
                    ],
                )
            ],
        )
        issues = validate_workflow(wf, [wf], {"s1": ["1"]})
        self.assertTrue(
            any("Invalid join_strategy 'invalid_strat'" in i.message for i in issues)
        )

    def test_validate_graph_rejects_legacy_noncanonical_join_strategies(self):
        for bad_join_strategy in ["array", "dict", "last"]:
            with self.subTest(join_strategy=bad_join_strategy):
                wf = WorkflowDef(
                    id="g1",
                    name="G1",
                    steps=[
                        StepDef(
                            id="s1",
                            name="s1",
                            model="m",
                            prompt_version="1",
                            execution_mode="graph",
                            inputs=[
                                InputPortDef(
                                    name="in1",
                                    join_strategy=bad_join_strategy,
                                    sources=[],
                                )
                            ],
                        )
                    ],
                )
                issues = validate_workflow(wf, [wf], {"s1": ["1"]})
                self.assertTrue(
                    any(
                        f"Invalid join_strategy '{bad_join_strategy}'" in i.message
                        for i in issues
                    )
                )

    def test_validate_graph_required_unsatisfied(self):
        wf = WorkflowDef(
            id="g1",
            name="G1",
            steps=[
                StepDef(
                    id="s1",
                    name="s1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[InputPortDef(name="in1", required=True, sources=[])],
                )
            ],
        )
        issues = validate_workflow(wf, [wf], {"s1": ["1"]})
        self.assertTrue(any("required but has no sources" in i.message for i in issues))

    def test_validate_graph_self_reference(self):
        wf = WorkflowDef(
            id="g1",
            name="G1",
            steps=[
                StepDef(
                    id="s1",
                    name="s1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="in1", sources=[SourceRef(step_id="s1", port="out")]
                        )
                    ],
                )
            ],
        )
        issues = validate_workflow(wf, [wf], {"s1": ["1"]})
        self.assertTrue(any("cannot self-reference" in i.message for i in issues))

    def test_validate_graph_missing_source_step(self):
        wf = WorkflowDef(
            id="g1",
            name="G1",
            steps=[
                StepDef(
                    id="s1",
                    name="s1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="in1",
                            sources=[SourceRef(step_id="missing", port="out")],
                        )
                    ],
                )
            ],
        )
        issues = validate_workflow(wf, [wf], {"s1": ["1"]})
        self.assertTrue(any("Source step 'missing'" in i.message for i in issues))

    def test_validate_graph_missing_source_port(self):
        wf = WorkflowDef(
            id="g1",
            name="G1",
            steps=[
                StepDef(
                    id="src",
                    name="src",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[],
                ),
                StepDef(
                    id="dest",
                    name="dest",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    inputs=[
                        InputPortDef(
                            name="in1",
                            sources=[SourceRef(step_id="src", port="bad_port")],
                        )
                    ],
                ),
            ],
        )
        issues = validate_workflow(wf, [wf], {"src": ["1"], "dest": ["1"]})
        self.assertTrue(
            any("Source port 'bad_port' does not exist" in i.message for i in issues)
        )

    def test_validate_graph_dependency_cycle(self):
        wf = WorkflowDef(
            id="g1",
            name="G1",
            steps=[
                StepDef(
                    id="s1",
                    name="s1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="out1", kind="text")],
                    inputs=[
                        InputPortDef(
                            name="in1", sources=[SourceRef(step_id="s2", port="out2")]
                        )
                    ],
                ),
                StepDef(
                    id="s2",
                    name="s2",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[OutputPortDef(name="out2", kind="text")],
                    inputs=[
                        InputPortDef(
                            name="in2", sources=[SourceRef(step_id="s1", port="out1")]
                        )
                    ],
                ),
            ],
        )
        issues = validate_workflow(wf, [wf], {"s1": ["1"], "s2": ["1"]})
        self.assertTrue(any("Circular dependency" in i.message for i in issues))

    def test_validate_graph_duplicate_output_port(self):
        wf = WorkflowDef(
            id="g1",
            name="G1",
            steps=[
                StepDef(
                    id="s1",
                    name="s1",
                    model="m",
                    prompt_version="1",
                    execution_mode="graph",
                    outputs=[
                        OutputPortDef(name="out1", kind="text"),
                        OutputPortDef(name="out1", kind="json"),
                    ],
                )
            ],
        )
        issues = validate_workflow(wf, [wf], {"s1": ["1"]})
        self.assertTrue(
            any("Duplicate output port name 'out1'" in i.message for i in issues)
        )


if __name__ == "__main__":
    unittest.main()
