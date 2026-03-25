import unittest

from ui.flow_canvas import ROOT_SOURCE_IDS, WORKFLOW_INPUT_EDGE_LABEL, incoming_peer_label


class TestFlowCanvasLabels(unittest.TestCase):
    def test_incoming_peer_label_root_source_ids(self):
        id_to_title = {"step_1": "Draft summary"}
        for source_id in ROOT_SOURCE_IDS:
            self.assertEqual(
                incoming_peer_label(source_id, id_to_title), WORKFLOW_INPUT_EDGE_LABEL
            )

    def test_incoming_peer_label_non_root_uses_title_fallback_id(self):
        id_to_title = {"step_1": "Draft summary"}
        self.assertEqual(incoming_peer_label("step_1", id_to_title), "Draft summary")
        self.assertEqual(incoming_peer_label("step_2", id_to_title), "step_2")

    def test_incoming_peer_label_blank_title_falls_back_to_id(self):
        id_to_title = {"step_1": ""}
        self.assertEqual(incoming_peer_label("step_1", id_to_title), "step_1")


if __name__ == "__main__":
    unittest.main()
