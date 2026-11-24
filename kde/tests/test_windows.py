"""Windows contracts, process identity safety, and real native API integration."""
import os
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

if sys.platform == "win32":
    import psutil
    from refract.backend import windows
    from refract.backend.windows_native import process_snapshot


@unittest.skipUnless(sys.platform == "win32", "Windows backend")
class WindowsTests(unittest.TestCase):
    def test_native_snapshot_matches_current_process(self):
        me = psutil.Process()
        row = next(r for r in process_snapshot() if r["pid"] == os.getpid())
        self.assertEqual(row["ppid"], me.ppid())
        self.assertEqual(windows._start_token(row["created"]), windows._start_token(me.create_time()))
        self.assertGreater(row["memory"], 0)
        self.assertGreater(row["threads"], 0)

    def test_snapshot_matches_ui_schema(self):
        sampler = windows.SystemSampler()
        try:
            sampler.sample()
            time.sleep(.1)
            snap = sampler.sample()
            self.assertEqual(set(snap), {"timestamp", "cpu", "memory", "disks", "network", "gpus", "fans", "batteries"})
            self.assertEqual(len(snap["cpu"]["per_core"]), psutil.cpu_count())
            self.assertTrue(0 <= snap["cpu"]["usage"] <= 100)
            self.assertGreater(snap["memory"]["total"], 0)
            self.assertLessEqual(snap["memory"]["available"], snap["memory"]["total"])
            self.assertTrue(all(d["id"] for d in snap["disks"]))
            self.assertEqual(sampler.static_info()["engine"], "windows")
        finally:
            sampler.close()
            self.assertFalse(sampler._pdh._query)

    def test_rates_reset_on_pid_reuse(self):
        def entry(created, cpu, read):
            return {"pid": os.getpid(), "ppid": 0, "threads": 1, "name": "test.exe", "created": created,
                    "cpu_seconds": cpu, "memory": 100, "read_bytes": read, "write_bytes": read}
        sampler = windows.ProcessSampler()
        with patch.object(windows, "process_snapshot", side_effect=[[entry(100, 1, 100)], [entry(100, 2, 200)], [entry(101, 50, 5000)]]):
            first = sampler.sample()[0]
            sampler._last -= 1
            second = sampler.sample()[0]
            third = sampler.sample()[0]
        self.assertEqual(first["cpu"], 0)
        self.assertGreater(second["cpu"], 0)
        self.assertGreater(second["disk_read_bps"], 0)
        self.assertEqual(third["cpu"], 0)
        self.assertIsNone(third["disk_read_bps"])
        self.assertNotEqual(first["start_ticks"], third["start_ticks"])

    def test_stale_identity_cannot_terminate_child(self):
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            token = windows._start_token(psutil.Process(child.pid).create_time())
            ok, _ = windows.signal_process(child.pid, "KILL", token - 1)
            self.assertFalse(ok)
            self.assertIsNone(child.poll())
            self.assertTrue(windows.signal_process(child.pid, "STOP", token)[0])
            self.assertEqual(psutil.Process(child.pid).status(), psutil.STATUS_STOPPED)
            self.assertTrue(windows.signal_process(child.pid, "CONT", token)[0])
            self.assertTrue(windows.signal_process(child.pid, "TERM", token)[0])
            child.wait(timeout=5)
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)

    def test_service_inventory_and_invalid_actions(self):
        rows = windows.list_services()
        self.assertTrue(rows)
        self.assertTrue(all(not r["user"] for r in rows))
        with patch.object(windows, "_run") as run:
            self.assertFalse(windows.service_action("anything", "invalid")[0])
            self.assertFalse(windows.service_action("-option", "start")[0])
            run.assert_not_called()

    def test_restart_waits_for_stop(self):
        with patch.object(windows.psutil, "win_service_get") as get, patch.object(windows, "_run") as run, patch.object(windows, "_wait_service", return_value=False):
            get.return_value.status.return_value = "running"
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            ok, error = windows.service_action("TestSvc", "restart")
            self.assertFalse(ok)
            self.assertIn("Timed out", error)
            run.assert_called_once_with(["sc.exe", "stop", "TestSvc"])

    def test_event_logs_match_exact_service(self):
        xml = '<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event"><System><EventID>7036</EventID><TimeCreated SystemTime="2026-10-07T12:00:00Z"/></System><EventData><Data>Test Service</Data><Data>running</Data></EventData></Event>'
        with patch.object(windows.psutil, "win_service_get") as get, patch.object(windows, "_run") as run:
            get.return_value.display_name.return_value = "Test Service"
            run.return_value = subprocess.CompletedProcess([], 0, xml, "")
            self.assertIn("Event 7036", windows.service_logs("TestSvc"))
            get.return_value.display_name.return_value = "Other Service"
            self.assertEqual(windows.service_logs("OtherSvc"), "")


if __name__ == "__main__":
    unittest.main()
