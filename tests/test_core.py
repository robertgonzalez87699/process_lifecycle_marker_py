import json
import unittest

from process_lifecycle_marker_py import LifecycleMarker, MarkerRecord


class FakeClock:
    """A deterministic clock that advances only when told to."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class MarkerRecordTests(unittest.TestCase):
    def test_to_json_contains_expected_keys(self) -> None:
        record = MarkerRecord(event="startup", boot_id="boot-1", uptime=1.5, pid=42)
        payload = json.loads(record.to_json())
        self.assertEqual(
            payload,
            {"event": "startup", "boot_id": "boot-1", "uptime": 1.5, "pid": 42},
        )

    def test_to_json_is_compact(self) -> None:
        record = MarkerRecord(event="shutdown", boot_id="boot-2", uptime=0.0, pid=7)
        self.assertNotIn(" ", record.to_json())


class LifecycleMarkerTests(unittest.TestCase):
    def test_startup_uses_initial_uptime(self) -> None:
        clock = FakeClock(start=100.0)
        marker = LifecycleMarker(boot_id="boot-a", clock=clock)
        record = marker.startup()
        self.assertEqual(record.event, "startup")
        self.assertEqual(record.boot_id, "boot-a")
        self.assertAlmostEqual(record.uptime, 0.0)
        self.assertIsInstance(record.pid, int)

    def test_shutdown_uptime_advances_with_clock(self) -> None:
        clock = FakeClock(start=100.0)
        marker = LifecycleMarker(boot_id="boot-b", clock=clock)
        marker.startup()
        clock.advance(2.5)
        record = marker.shutdown()
        self.assertEqual(record.event, "shutdown")
        self.assertEqual(record.boot_id, "boot-b")
        self.assertAlmostEqual(record.uptime, 2.5)

    def test_records_share_boot_id(self) -> None:
        clock = FakeClock()
        marker = LifecycleMarker(boot_id="boot-c", clock=clock)
        start = marker.startup()
        clock.advance(1.0)
        stop = marker.shutdown()
        self.assertEqual(start.boot_id, stop.boot_id)

    def test_double_startup_raises(self) -> None:
        clock = FakeClock()
        marker = LifecycleMarker(boot_id="boot-d", clock=clock)
        marker.startup()
        with self.assertRaises(RuntimeError):
            marker.startup()

    def test_shutdown_before_startup_raises(self) -> None:
        clock = FakeClock()
        marker = LifecycleMarker(boot_id="boot-e", clock=clock)
        with self.assertRaises(RuntimeError):
            marker.shutdown()

    def test_double_shutdown_raises(self) -> None:
        clock = FakeClock()
        marker = LifecycleMarker(boot_id="boot-f", clock=clock)
        marker.startup()
        marker.shutdown()
        with self.assertRaises(RuntimeError):
            marker.shutdown()

    def test_uptime_is_immune_to_non_monotonic_clock(self) -> None:
        clock = FakeClock(start=10.0)
        marker = LifecycleMarker(boot_id="boot-g", clock=clock)
        marker.startup()
        clock.now = 5.0
        record = marker.shutdown()
        self.assertAlmostEqual(record.uptime, -5.0)

    def test_default_clock_is_monotonic(self) -> None:
        marker = LifecycleMarker(boot_id="boot-h")
        record = marker.startup()
        self.assertGreaterEqual(record.uptime, 0.0)


if __name__ == "__main__":
    unittest.main()
