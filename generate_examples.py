import os
import json
from core.models import WorkflowDef, StepDef, InputPortDef, OutputPortDef


def create_examples():
    os.makedirs("examples", exist_ok=True)

    # Example 1: Fan-out, Fan-in
    wf1 = WorkflowDef(
        id="wf_graph_fanout",
        name="Graph: 3-Way Parallel Analysis",
        description="Fanning out a task and merging the parallel processing results.",
        schema_version=3,
    )

    s_start = StepDef(
        id="starter",
        title="Extract Raw Text",
        name="starter",
        execution_mode="graph",
        inputs=[InputPortDef("in1", "Document File", required=False)],
        outputs=[OutputPortDef("out_text", "Extracted Text")],
    )

    s_b1 = StepDef(
        id="branch_1",
        title="Analyze Readability",
        name="b1",
        execution_mode="graph",
        inputs=[InputPortDef("in_text", "Document Text", "starter", "out_text")],
        outputs=[OutputPortDef("out_result", "Readability Score")],
        depends_on=["starter"],
    )

    s_b2 = StepDef(
        id="branch_2",
        title="Analyze Sentiment",
        name="b2",
        execution_mode="graph",
        inputs=[InputPortDef("in_text", "Document Text", "starter", "out_text")],
        outputs=[OutputPortDef("out_result", "Sentiment Score")],
        depends_on=["starter"],
    )

    s_b3 = StepDef(
        id="branch_3",
        title="Extract Key Entities",
        name="b3",
        execution_mode="graph",
        inputs=[InputPortDef("in_text", "Document Text", "starter", "out_text")],
        outputs=[OutputPortDef("out_result", "Entities List")],
        depends_on=["starter"],
    )

    s_merge = StepDef(
        id="merger",
        title="Compile Executive Summary",
        name="merge",
        execution_mode="graph",
        inputs=[
            InputPortDef("in1", "Readability", "branch_1", "out_result"),
            InputPortDef("in2", "Sentiment", "branch_2", "out_result"),
            InputPortDef("in3", "Entities", "branch_3", "out_result"),
        ],
        outputs=[OutputPortDef("out_final", "Executive Summary")],
        depends_on=["branch_1", "branch_2", "branch_3"],
    )

    wf1.steps = [s_start, s_b1, s_b2, s_b3, s_merge]

    with open("examples/graph_fanout.json", "w") as f:
        json.dump(wf1.to_dict(), f, indent=2)

    # Example 2: Multi-output
    wf2 = WorkflowDef(
        id="wf_graph_multi_out",
        name="Graph: Multi-Output Validation",
        description="A step produces two distinct outputs, which are processed independently.",
        schema_version=3,
    )

    s_gen = StepDef(
        id="generator",
        title="Generate Code & Tests",
        name="gen",
        execution_mode="graph",
        inputs=[InputPortDef("reqs", "Requirements")],
        outputs=[
            OutputPortDef("out_code", "Source Code"),
            OutputPortDef("out_tests", "Test Cases"),
        ],
    )

    s_lint = StepDef(
        id="lint",
        title="Lint Code",
        name="lint",
        execution_mode="graph",
        inputs=[InputPortDef("code", "Code to Lint", "generator", "out_code")],
        outputs=[OutputPortDef("lint_report", "Lint Report")],
        depends_on=["generator"],
    )

    s_run_tests = StepDef(
        id="run_tests",
        title="Execute Tests",
        name="tester",
        execution_mode="graph",
        inputs=[
            InputPortDef("src", "Source", "generator", "out_code"),
            InputPortDef("tests", "Tests", "generator", "out_tests"),
        ],
        outputs=[OutputPortDef("test_results", "Test Results")],
        depends_on=["generator"],
    )

    wf2.steps = [s_gen, s_lint, s_run_tests]

    with open("examples/graph_multi_out.json", "w") as f:
        json.dump(wf2.to_dict(), f, indent=2)


if __name__ == "__main__":
    create_examples()
