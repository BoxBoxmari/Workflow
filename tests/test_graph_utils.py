from core.models import StepDef, InputPortDef, SourceRef
from core.graph_utils import build_predecessor_map, extract_port_bindings


def test_build_predecessor_map_legacy():
    steps = [
        StepDef(
            id="a", name="a", model="m", prompt_version="1", execution_mode="legacy"
        ),
        StepDef(
            id="b",
            name="b",
            model="m",
            prompt_version="1",
            execution_mode="legacy",
            depends_on=["a"],
        ),
        StepDef(
            id="c",
            name="c",
            model="m",
            prompt_version="1",
            execution_mode="legacy",
            depends_on=["a", "b"],
        ),
    ]

    preds = build_predecessor_map(steps)
    assert preds["a"] == []
    assert preds["b"] == ["a"]
    assert set(preds["c"]) == {"a", "b"}


def test_build_predecessor_map_graph():
    steps = [
        StepDef(
            id="src1",
            name="src1",
            model="m",
            prompt_version="1",
            execution_mode="graph",
            outputs=[],
        ),
        StepDef(
            id="src2",
            name="src2",
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
                    name="in1", sources=[SourceRef(step_id="src1", port="out")]
                ),
                InputPortDef(
                    name="in2", sources=[SourceRef(step_id="src2", port="out")]
                ),
            ],
        ),
    ]

    preds = build_predecessor_map(steps)
    assert preds["src1"] == []
    assert preds["src2"] == []
    assert set(preds["dest"]) == {"src1", "src2"}


def test_extract_port_bindings():
    step = StepDef(
        id="dest",
        name="dest",
        model="m",
        prompt_version="1",
        execution_mode="graph",
        inputs=[
            InputPortDef(
                name="in1",
                sources=[
                    SourceRef(step_id="src1", port="out1"),
                    SourceRef(step_id="src1", port="out2"),
                ],
            ),
            InputPortDef(name="in2", sources=[SourceRef(step_id="src2", port="out")]),
        ],
    )

    bindings = extract_port_bindings(step)
    assert len(bindings) == 3
    assert bindings[0] == {
        "input_port": "in1",
        "source_step": "src1",
        "source_port": "out1",
    }
    assert bindings[1] == {
        "input_port": "in1",
        "source_step": "src1",
        "source_port": "out2",
    }
    assert bindings[2] == {
        "input_port": "in2",
        "source_step": "src2",
        "source_port": "out",
    }


def test_extract_port_bindings_legacy():
    step = StepDef(
        id="dest",
        name="dest",
        model="m",
        prompt_version="1",
        execution_mode="legacy",
        depends_on=["src"],
    )
    bindings = extract_port_bindings(step)
    assert bindings == []
