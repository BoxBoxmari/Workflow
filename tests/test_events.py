"""Tests for core.events — EventBus publish/subscribe/dispatch."""

import unittest

from core.events import Event, EventBus, run_started, step_started


class TestEventBusPubSub(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()

    def test_subscribe_and_receive(self):
        received = []
        self.bus.subscribe("test.event", lambda e: received.append(e))
        self.bus.publish({"type": "test.event", "value": 42})
        self.bus.dispatch()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["value"], 42)

    def test_multiple_subscribers(self):
        calls = []
        self.bus.subscribe("x", lambda e: calls.append("a"))
        self.bus.subscribe("x", lambda e: calls.append("b"))
        self.bus.publish({"type": "x"})
        self.bus.dispatch()
        self.assertIn("a", calls)
        self.assertIn("b", calls)

    def test_no_subscriber_for_type(self):
        # Should not raise
        self.bus.publish({"type": "unregistered"})
        count = self.bus.dispatch()
        self.assertEqual(count, 1)  # event dispatched, no subscribers

    def test_dispatch_returns_count(self):
        self.bus.publish({"type": "a"})
        self.bus.publish({"type": "b"})
        count = self.bus.dispatch()
        self.assertEqual(count, 2)

    def test_dispatch_empties_queue(self):
        self.bus.publish({"type": "a"})
        self.bus.dispatch()
        count = self.bus.dispatch()
        self.assertEqual(count, 0)

    def test_unsubscribe(self):
        received = []
        token = self.bus.subscribe("evt", lambda e: received.append(e))
        self.bus.unsubscribe("evt", token)
        self.bus.publish({"type": "evt"})
        self.bus.dispatch()
        self.assertEqual(received, [])

    def test_wildcard_subscriber(self):
        received = []
        self.bus.subscribe("*", lambda e: received.append(e))
        self.bus.publish({"type": "anything"})
        self.bus.dispatch()
        self.assertEqual(len(received), 1)

    def test_publish_empty_event_does_not_raise(self):
        # Event with no 'type' key
        self.bus.publish({})
        self.bus.dispatch()  # Should not raise

    def test_subscriber_exception_does_not_block_others(self):
        calls = []

        def bad_handler(e):
            raise RuntimeError("boom")

        def good_handler(e):
            calls.append(e)

        self.bus.subscribe("evt", bad_handler)
        self.bus.subscribe("evt", good_handler)
        self.bus.publish({"type": "evt"})
        self.bus.dispatch()  # Should not raise
        self.assertEqual(len(calls), 1)

    def test_publish_event_dataclass_handlers_receive_dict(self):
        received = []
        self.bus.subscribe("run_started", lambda e: received.append(e))
        self.bus.publish(run_started("r1", "w1"))
        self.bus.dispatch()
        self.assertEqual(len(received), 1)
        e0 = received[0]
        self.assertIsInstance(e0, dict)
        self.assertEqual(e0.get("type"), "run_started")
        self.assertEqual(e0.get("run_id"), "r1")
        self.assertEqual(e0.get("workflow_id"), "w1")
        self.assertNotIn("_event", e0)

    def test_publish_event_wildcard_receives_dict_without_event_object(self):
        received = []
        self.bus.subscribe("*", lambda e: received.append(e))
        self.bus.publish(step_started("r1", "s1", 0, 3))
        self.bus.dispatch()
        self.assertEqual(len(received), 1)
        e0 = received[0]
        self.assertIsInstance(e0, dict)
        self.assertEqual(e0.get("type"), "step_started")
        self.assertEqual(e0.get("step_id"), "s1")
        self.assertNotIn("_event", e0)

    def test_publish_plain_event_constructor(self):
        received = []
        self.bus.subscribe("custom", lambda e: received.append(e))
        self.bus.publish(Event("custom", {"foo": 1}))
        self.bus.dispatch()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].get("type"), "custom")
        self.assertEqual(received[0].get("foo"), 1)


class TestEventBusThreadSafety(unittest.TestCase):
    """Minimal thread-safety check: publish from another thread."""

    def test_publish_from_thread(self):
        import threading

        bus = EventBus()
        received = []
        bus.subscribe("t", lambda e: received.append(e))

        def publisher():
            for i in range(10):
                bus.publish({"type": "t", "i": i})

        t = threading.Thread(target=publisher)
        t.start()
        t.join()
        count = bus.dispatch()
        self.assertEqual(count, 10)
        self.assertEqual(len(received), 10)


if __name__ == "__main__":
    unittest.main()
