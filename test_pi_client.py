#!/usr/bin/env python3
"""
Unit tests for pi_client.py

Tests the PiRPCClient and PiAgentPool classes using mocks so the tests do not
require an actual pi coding agent installation.
"""

import queue  # Imported to mirror module usage and ensure availability
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from pi_client import PiAgentPool, PiEvent, PiRPCClient, run_pi_once


class TestPiEvent(unittest.TestCase):
    """Tests for PiEvent dataclass"""

    def test_create_event(self):
        """Event should retain provided values"""
        event = PiEvent(type="text", data={"content": "hello"}, raw='{"type":"text"}')

        self.assertEqual(event.type, "text")
        self.assertEqual(event.data["content"], "hello")
        self.assertEqual(event.raw, '{"type":"text"}')

    def test_default_values(self):
        """Ensure defaults are applied when omitted"""
        event = PiEvent(type="completion")

        self.assertEqual(event.data, {})
        self.assertEqual(event.raw, "")


class TestPiRPCClient(unittest.TestCase):
    """Tests for PiRPCClient class"""

    def test_init_defaults(self):
        client = PiRPCClient()

        self.assertEqual(client.model, "claude-sonnet-4-5")
        self.assertIsNone(client.process)
        self.assertFalse(client._running)

    def test_init_custom_model(self):
        client = PiRPCClient(model="gpt-4", cwd=Path("/tmp"))

        self.assertEqual(client.model, "gpt-4")
        self.assertEqual(client.cwd, Path("/tmp"))

    @patch("shutil.which")
    def test_start_pi_not_found(self, mock_which):
        mock_which.return_value = None
        client = PiRPCClient()

        result = client.start()

        self.assertFalse(result)

    @patch("shutil.which")
    @patch("subprocess.Popen")
    def test_start_success(self, mock_popen, mock_which):
        mock_which.return_value = "/usr/bin/pi"
        mock_process = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout.readline.return_value = ""
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        client = PiRPCClient()
        result = client.start()

        self.assertTrue(result)
        self.assertTrue(client._running)
        self.assertIs(client.process, mock_process)

    def test_execute_not_started(self):
        client = PiRPCClient()
        response, error = client.execute("test prompt")

        self.assertIsNone(response)
        self.assertEqual(error, "Pi client not started")

    def test_stop_not_started(self):
        client = PiRPCClient()

        client.stop()  # Should not raise

        self.assertFalse(client._running)

    @patch("shutil.which")
    @patch("subprocess.Popen")
    def test_stop_terminates_process(self, mock_popen, mock_which):
        mock_which.return_value = "/usr/bin/pi"
        mock_process = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdout.readline.return_value = ""
        mock_process.poll.return_value = None
        mock_process.pid = 99999
        mock_popen.return_value = mock_process

        client = PiRPCClient()
        client.start()
        client.stop()

        self.assertFalse(client._running)
        mock_process.terminate.assert_called()

    def test_is_running_false_initially(self):
        client = PiRPCClient()

        self.assertFalse(client.is_running())

    def test_context_manager(self):
        with patch("shutil.which", return_value=None):
            with PiRPCClient() as client:
                self.assertIsInstance(client, PiRPCClient)


class TestPiAgentPool(unittest.TestCase):
    """Tests for PiAgentPool class"""

    def test_init_defaults(self):
        pool = PiAgentPool()

        self.assertEqual(pool.size, 3)
        self.assertEqual(pool.model, "claude-sonnet-4-5")
        self.assertEqual(pool.agents, {})

    def test_init_custom(self):
        pool = PiAgentPool(size=6, model="gpt-4")

        self.assertEqual(pool.size, 6)
        self.assertEqual(pool.model, "gpt-4")

    @patch("pi_client.PiRPCClient")
    def test_get_agent_creates_new(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.start.return_value = True
        mock_client.is_running.return_value = True
        mock_client_class.return_value = mock_client

        pool = PiAgentPool()
        agent = pool.get_agent("test_agent", cwd=Path("/tmp"))

        self.assertEqual(agent, mock_client)
        self.assertIn("test_agent", pool.agents)

    @patch("pi_client.PiRPCClient")
    def test_get_agent_returns_existing(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.start.return_value = True
        mock_client.is_running.return_value = True
        mock_client_class.return_value = mock_client

        pool = PiAgentPool()
        agent1 = pool.get_agent("test_agent")
        agent2 = pool.get_agent("test_agent")

        self.assertIs(agent1, agent2)
        self.assertEqual(mock_client_class.call_count, 1)

    @patch("pi_client.PiRPCClient")
    def test_get_agent_replaces_dead(self, mock_client_class):
        mock_client1 = MagicMock()
        mock_client1.start.return_value = True
        mock_client1.is_running.return_value = False

        mock_client2 = MagicMock()
        mock_client2.start.return_value = True
        mock_client2.is_running.return_value = True

        mock_client_class.side_effect = [mock_client1, mock_client2]

        pool = PiAgentPool()
        agent1 = pool.get_agent("test_agent")
        agent2 = pool.get_agent("test_agent")

        self.assertIs(agent1, mock_client1)
        self.assertIs(agent2, mock_client2)
        self.assertEqual(mock_client_class.call_count, 2)
        mock_client1.stop.assert_called()

    @patch("pi_client.PiRPCClient")
    def test_get_agent_start_fails(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.start.return_value = False
        mock_client_class.return_value = mock_client

        pool = PiAgentPool()

        with self.assertRaises(RuntimeError):
            pool.get_agent("test_agent")

    @patch("pi_client.PiRPCClient")
    def test_stop_agent(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.start.return_value = True
        mock_client.is_running.return_value = True
        mock_client_class.return_value = mock_client

        pool = PiAgentPool()
        pool.get_agent("test_agent")
        pool.stop_agent("test_agent")

        mock_client.stop.assert_called()
        self.assertNotIn("test_agent", pool.agents)

    @patch("pi_client.PiRPCClient")
    def test_cleanup(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.start.return_value = True
        mock_client.is_running.return_value = True
        mock_client_class.return_value = mock_client

        pool = PiAgentPool()
        pool.get_agent("agent1")
        pool.get_agent("agent2")
        pool.cleanup()

        mock_client.stop.assert_called()
        self.assertEqual(len(pool.agents), 0)

    @patch("pi_client.PiRPCClient")
    def test_active_count(self, mock_client_class):
        mock_client1 = MagicMock()
        mock_client1.start.return_value = True
        mock_client1.is_running.return_value = True

        mock_client2 = MagicMock()
        mock_client2.start.return_value = True
        mock_client2.is_running.return_value = False

        mock_client_class.side_effect = [mock_client1, mock_client2]

        pool = PiAgentPool()
        pool.get_agent("agent1")
        pool.agents["agent2"] = mock_client2

        self.assertEqual(pool.active_count(), 1)

    def test_context_manager(self):
        with PiAgentPool() as pool:
            self.assertIsInstance(pool, PiAgentPool)


class TestRunPiOnce(unittest.TestCase):
    """Tests for run_pi_once helper"""

    @patch("pi_client.PiRPCClient")
    def test_run_pi_once(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.start.return_value = True
        mock_client.execute.return_value = ("response", None)

        def exit_side_effect(exc_type, exc, tb):
            mock_client.stop()
            return False

        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.side_effect = exit_side_effect
        mock_client_class.return_value = mock_client

        response, error = run_pi_once("test prompt", timeout=60)

        self.assertEqual(response, "response")
        self.assertIsNone(error)
        mock_client.stop.assert_called()


if __name__ == "__main__":
    unittest.main()
