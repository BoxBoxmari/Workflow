import unittest

from ui.inspector_panel import (
    CANONICAL_WORKFLOW_ROOT_STEP_ID,
    INSPECTOR_ROOT_SOURCE_DISPLAY,
    JOIN_STRATEGY_LABEL_TO_VALUE,
    NO_SOURCE_LABEL,
    canonical_source_step_id_from_combo,
    join_strategy_to_label,
    join_strategy_to_value,
    normalized_source_ref_from_choice,
    parse_title_id_suffix,
)


class TestNonTechnicalAuthoring(unittest.TestCase):
    def test_source_combo_no_source_persists_empty(self):
        self.assertEqual(canonical_source_step_id_from_combo(""), "")
        self.assertEqual(canonical_source_step_id_from_combo(NO_SOURCE_LABEL), "")
        self.assertEqual(canonical_source_step_id_from_combo("(no source step)"), "")

    def test_source_combo_root_persists_canonical_input(self):
        self.assertEqual(
            canonical_source_step_id_from_combo(INSPECTOR_ROOT_SOURCE_DISPLAY),
            CANONICAL_WORKFLOW_ROOT_STEP_ID,
        )
        self.assertEqual(
            canonical_source_step_id_from_combo("Workflow input (__input__)"),
            CANONICAL_WORKFLOW_ROOT_STEP_ID,
        )

    def test_source_ref_normalization_enforces_root_input_port(self):
        self.assertEqual(
            normalized_source_ref_from_choice(INSPECTOR_ROOT_SOURCE_DISPLAY, "output"),
            (CANONICAL_WORKFLOW_ROOT_STEP_ID, "input"),
        )
        self.assertEqual(
            normalized_source_ref_from_choice("Workflow input (__input__)", ""),
            (CANONICAL_WORKFLOW_ROOT_STEP_ID, "input"),
        )

    def test_source_ref_normalization_defaults_non_root_to_output(self):
        self.assertEqual(
            normalized_source_ref_from_choice("Draft summary (step_2)", ""),
            ("step_2", "output"),
        )
        self.assertEqual(
            normalized_source_ref_from_choice("Draft summary (step_2)", "json"),
            ("step_2", "json"),
        )

    def test_source_combo_title_id_suffix_parses_step_id(self):
        parsed = parse_title_id_suffix("Draft summary (step_2)")
        self.assertEqual(parsed, ("Draft summary", "step_2"))
        self.assertEqual(
            canonical_source_step_id_from_combo("Draft summary (step_2)"),
            "step_2",
        )

    def test_join_strategy_uses_user_facing_labels(self):
        self.assertIn("Use first available", JOIN_STRATEGY_LABEL_TO_VALUE)
        self.assertIn("Combine all (list)", JOIN_STRATEGY_LABEL_TO_VALUE)
        self.assertIn("Combine by source name", JOIN_STRATEGY_LABEL_TO_VALUE)

    def test_join_strategy_label_to_canonical_mapping(self):
        self.assertEqual(
            join_strategy_to_value("Use first available"),
            "first",
        )
        self.assertEqual(
            join_strategy_to_value("Combine all (list)"),
            "concat",
        )
        self.assertEqual(
            join_strategy_to_value("Combine by source name"),
            "json_map",
        )

    def test_join_strategy_roundtrip(self):
        self.assertEqual(
            join_strategy_to_label("first"),
            "Use first available",
        )
        self.assertEqual(
            join_strategy_to_label("concat"),
            "Combine all (list)",
        )
        self.assertEqual(
            join_strategy_to_label("json_map"), "Combine by source name"
        )
        self.assertEqual(
            join_strategy_to_value(join_strategy_to_label("first")),
            "first",
        )
        self.assertEqual(
            join_strategy_to_value(join_strategy_to_label("concat")), "concat"
        )
        self.assertEqual(
            join_strategy_to_value(join_strategy_to_label("json_map")),
            "json_map",
        )


if __name__ == "__main__":
    unittest.main()
