#!/usr/bin/env python3
"""
Pi Coding Agent RPC Client Module

This module provides a Python interface to the pi coding agent via its RPC mode.
The pi agent communicates using JSON line-delimited protocol over stdin/stdout.

RPC Protocol:
    - Input: JSON objects sent to stdin, one per line
    - Output: JSON objects received from stdout, one per line

Event Types:
    - "text": Streaming text content (accumulate for full response)
    - "tool_call": Agent is using a tool (file operations, bash, etc.)
    - "tool_result": Result from a tool execution
    - "completion": Agent has finished processing
    - "error": An error occurred

Usage:
    from pi_client import PiRPCClient, PiAgentPool

    # Single client
    client = PiRPCClient(model="claude-sonnet-4-5", cwd=Path("/path/to/repo"))
    client.start()
    response, error = client.execute("Create a hello.py file", timeout=300)
    client.stop()

    # Pool for parallel execution
    pool = PiAgentPool(size=6, model="claude-sonnet-4-5")
    agent = pool.get_agent("manager_a", cwd=Path("/path/to/worktree"))
    response, error = agent.execute("Implement feature X", timeout=600)
    pool.cleanup()
"""

import json
import subprocess
import threading
import time
import queue
import signal
import os
import shutil
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class PiEvent:
    """Represents an event from the pi RPC protocol."""

    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""


class PiRPCClient:
    """
    RPC client for communicating with pi coding agent.

    The pi agent runs as a subprocess in RPC mode, accepting JSON commands
    via stdin and returning JSON events via stdout.

    Attributes:
        model: The AI model to use (e.g., "claude-sonnet-4-5")
        cwd: Working directory for the pi process
        process: The subprocess running pi
        _running: Whether the client is currently active
    """

    def __init__(self, model: str = "claude-sonnet-4-5", cwd: Optional[Path] = None):
        """
        Initialize the RPC client.

        Args:
            model: AI model identifier (default: claude-sonnet-4-5)
            cwd: Working directory for pi process (default: current directory)
        """
        self.model = model
        self.cwd = cwd or Path.cwd()
        self.process: Optional[subprocess.Popen] = None
        self._running = False
        self._output_queue: queue.Queue[PiEvent] = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._response_text = ""
        self._error_text = ""
        self._completion_event = threading.Event()

    def start(self) -> bool:
        """
        Start the pi process in RPC mode.

        Returns:
            True if process started successfully, False otherwise
        """
        if self._running:
            return True

        # Find pi executable - check common install locations
        pi_path = shutil.which("pi")
        if not pi_path:
            # Check common npm global install location
            npm_global_pi = Path.home() / ".npm-global" / "bin" / "pi"
            if npm_global_pi.exists():
                pi_path = str(npm_global_pi)
            else:
                return False

        try:
            # Start pi in RPC mode with specified model
            # --rpc: Enable RPC mode (JSON line protocol)
            # --model: Specify the AI model to use
            # --non-interactive: Disable interactive prompts
            cmd = [pi_path, "--rpc", "--model", self.model, "--non-interactive"]

            self.process = subprocess.Popen(
                cmd,
                cwd=str(self.cwd),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                # Ensure process is in its own process group for clean termination
                preexec_fn=os.setsid if os.name != "nt" else None,
            )

            self._running = True

            # Start background thread to read output
            self._reader_thread = threading.Thread(
                target=self._read_output, daemon=True, name=f"pi-reader-{id(self)}"
            )
            self._reader_thread.start()

            return True

        except Exception as e:
            self._running = False
            return False

    def _read_output(self):
        """
        Background thread to read JSON lines from pi's stdout.

        This method runs continuously, parsing JSON events and placing
        them in the output queue for processing by execute().
        """
        if not self.process or not self.process.stdout:
            return

        while self._running and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if not line:
                    # EOF or process terminated
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    event_type = data.get("type", "unknown")

                    event = PiEvent(type=event_type, data=data, raw=line)

                    self._output_queue.put(event)

                except json.JSONDecodeError:
                    # Non-JSON output, treat as raw text
                    event = PiEvent(type="raw", data={"content": line}, raw=line)
                    self._output_queue.put(event)

            except Exception:
                # Reader thread should not crash
                if self._running:
                    continue
                break

        # Signal completion when process ends
        self._output_queue.put(PiEvent(type="process_exit", data={}))

    def execute(
        self,
        prompt: str,
        timeout: Optional[int] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Execute a prompt and return the response.

        Args:
            prompt: The task/prompt to send to pi
            timeout: Maximum time to wait in seconds (None = no timeout)
            on_chunk: Optional callback for streaming text chunks

        Returns:
            Tuple of (response_text, error_message)
            - On success: (response_text, None)
            - On error: (None, error_message)
        """
        if not self._running or not self.process:
            return None, "Pi client not started"

        if not self.process.stdin:
            return None, "Pi process stdin not available"

        # Reset state for new execution
        self._response_text = ""
        self._error_text = ""
        self._completion_event.clear()

        # Clear any pending events from previous execution
        while not self._output_queue.empty():
            try:
                self._output_queue.get_nowait()
            except queue.Empty:
                break

        # Send the prompt as a JSON message
        # Pi RPC protocol expects: {"type": "prompt", "content": "..."}
        message = {"type": "prompt", "content": prompt}

        try:
            self.process.stdin.write(json.dumps(message) + "\n")
            self.process.stdin.flush()
        except Exception as e:
            return None, f"Failed to send prompt: {e}"

        # Process events until completion or timeout
        start_time = time.time()
        last_activity = time.time()
        completed = False
        has_activity = False  # Track if we've seen any activity
        inactivity_threshold = 10  # seconds of inactivity before checking completion

        while not completed:
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                return None, f"Timeout after {timeout}s"

            # Check if process is still running
            returncode = self.process.poll()
            if returncode is not None:
                # Process exited
                if returncode == 0 and has_activity:
                    # Clean exit with activity = success
                    completed = True
                    break
                elif returncode == 0:
                    # Clean exit but no activity - might still be success
                    # Give it a moment to see if session logs appear
                    time.sleep(2)
                    if self._has_session_output():
                        completed = True
                        break
                    return None, "Pi process exited without producing output"
                else:
                    return None, f"Pi process exited with code {returncode}"

            # Check for completion via inactivity after receiving activity
            if has_activity:
                elapsed_since_activity = time.time() - last_activity
                if elapsed_since_activity > inactivity_threshold:
                    # Long inactivity after activity - check if work is done
                    if self._has_session_output():
                        completed = True
                        break

            try:
                # Wait for next event with short timeout for responsiveness
                event = self._output_queue.get(timeout=1.0)
                last_activity = time.time()
                has_activity = True

                # Handle different event types
                if event.type == "text":
                    # Streaming text content
                    content = event.data.get("content", "")
                    if not content:
                        # Alternative format: {"part": {"text": "..."}}
                        part = event.data.get("part", {})
                        content = part.get("text", "")

                    if content:
                        self._response_text += content
                        if on_chunk:
                            on_chunk(content)

                elif event.type == "tool_call":
                    # Agent is using a tool (file write, bash, etc.)
                    pass

                elif event.type == "tool_result":
                    # Result from a tool execution
                    pass

                elif event.type == "completion":
                    # Agent finished processing
                    completed = True
                    final_content = event.data.get("content", "")
                    if final_content and not self._response_text:
                        self._response_text = final_content

                elif event.type == "message.complete":
                    # Alternative completion format
                    completed = True
                    final_content = event.data.get("content", "")
                    if final_content:
                        self._response_text = final_content

                elif event.type == "error":
                    # Error occurred
                    error_msg = event.data.get("message", "Unknown error")
                    self._error_text = error_msg
                    return None, error_msg

                elif event.type == "process_exit":
                    # Process terminated - check if we have output
                    if has_activity or self._has_session_output():
                        completed = True
                    break

                elif event.type == "raw":
                    # Non-JSON output, append to response
                    content = event.data.get("content", "")
                    if content:
                        self._response_text += content
                        if on_chunk:
                            on_chunk(content)

            except queue.Empty:
                # No event received, continue waiting
                pass

        # Return based on what we collected
        if self._response_text:
            return self._response_text, None
        elif has_activity or self._has_session_output():
            return "Task completed", None
        elif self._error_text:
            return None, self._error_text
        else:
            return None, "No response received"

    def _has_session_output(self) -> bool:
        """
        Check if pi has created session output (indicating work was done).
        
        Returns:
            True if session logs exist with completion markers, False otherwise
        """
        try:
            pi_sessions = Path.home() / ".pi" / "agent" / "sessions"
            if not pi_sessions.exists():
                return False
            
            # Build expected session directory name pattern
            # Pi creates dirs like: --{cwd_path_with_dashes}--
            cwd_parts = str(self.cwd).lstrip('/').replace('/', '-')
            expected_pattern = f"--{cwd_parts}--"
            
            for session_dir in pi_sessions.iterdir():
                if not session_dir.is_dir():
                    continue
                    
                # Check if this session dir matches our cwd
                if expected_pattern not in session_dir.name:
                    continue
                
                # Check if it has recent session files with completion
                session_files = list(session_dir.glob("*.jsonl"))
                if not session_files:
                    continue
                    
                # Check the most recent file for completion markers
                latest = max(session_files, key=lambda p: p.stat().st_mtime)
                
                # File must be recent (within last 2 minutes)
                age = time.time() - latest.stat().st_mtime
                if age > 120:
                    continue
                
                # Check if file contains completion markers
                try:
                    with open(latest, 'r') as f:
                        # Read last 1KB to check for completion
                        f.seek(0, 2)  # Go to end
                        file_size = f.tell()
                        read_size = min(1024, file_size)
                        f.seek(max(0, file_size - read_size))
                        tail = f.read()
                        
                        # Look for stopReason indicators
                        if '"stopReason":"stop"' in tail or '"stopReason":"end_turn"' in tail:
                            return True
                except:
                    pass
            
            return False
            
        except Exception:
            return False

    def stop(self):
        """
        Terminate the pi process cleanly.

        This method ensures no zombie processes are left behind by:
        1. Sending SIGTERM to the process group
        2. Waiting briefly for graceful shutdown
        3. Sending SIGKILL if process doesn't terminate
        """
        self._running = False

        if not self.process:
            return

        try:
            # First, try graceful termination
            if self.process.poll() is None:
                # Send SIGTERM to process group (kills all child processes)
                if os.name != "nt":
                    try:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                    except (ProcessLookupError, PermissionError):
                        self.process.terminate()
                else:
                    self.process.terminate()

                # Wait up to 5 seconds for graceful shutdown
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if still running
                    if os.name != "nt":
                        try:
                            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            self.process.kill()
                    else:
                        self.process.kill()

                    # Final wait
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass

        except Exception:
            # Best effort cleanup
            pass
        finally:
            # Close file handles
            if self.process.stdin:
                try:
                    self.process.stdin.close()
                except Exception:
                    pass
            if self.process.stdout:
                try:
                    self.process.stdout.close()
                except Exception:
                    pass
            if self.process.stderr:
                try:
                    self.process.stderr.close()
                except Exception:
                    pass

            self.process = None

    def is_running(self) -> bool:
        """Check if the pi process is currently running."""
        return (
            self._running and self.process is not None and self.process.poll() is None
        )

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


class PiAgentPool:
    """
    Pool of pi RPC clients for parallel execution.

    This class manages multiple pi processes, allowing parallel execution
    of tasks across different working directories (e.g., git worktrees).

    Attributes:
        size: Maximum number of agents in the pool
        model: AI model to use for all agents
        agents: Dictionary mapping agent IDs to PiRPCClient instances
    """

    def __init__(self, size: int = 3, model: str = "claude-sonnet-4-5"):
        """
        Initialize the agent pool.

        Args:
            size: Maximum number of concurrent agents
            model: AI model identifier for all agents
        """
        self.size = size
        self.model = model
        self.agents: Dict[str, PiRPCClient] = {}
        self._lock = threading.Lock()

    def get_agent(self, agent_id: str, cwd: Optional[Path] = None) -> PiRPCClient:
        """
        Get or create an agent for the given ID.

        If an agent with the given ID already exists and is running,
        it will be returned. Otherwise, a new agent is created.

        Args:
            agent_id: Unique identifier for this agent (e.g., "manager_a")
            cwd: Working directory for the agent

        Returns:
            PiRPCClient instance ready for use
        """
        with self._lock:
            # Check if agent exists and is still running
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                if agent.is_running():
                    return agent
                else:
                    # Agent died, clean it up
                    agent.stop()
                    del self.agents[agent_id]

            # Create new agent
            agent = PiRPCClient(model=self.model, cwd=cwd)
            if agent.start():
                self.agents[agent_id] = agent
                return agent
            else:
                raise RuntimeError(f"Failed to start pi agent for {agent_id}")

    def stop_agent(self, agent_id: str):
        """
        Stop a specific agent.

        Args:
            agent_id: ID of the agent to stop
        """
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].stop()
                del self.agents[agent_id]

    def cleanup(self):
        """
        Stop all agents in the pool.

        This method ensures all pi processes are terminated cleanly,
        preventing zombie processes.
        """
        with self._lock:
            for agent_id, agent in list(self.agents.items()):
                try:
                    agent.stop()
                except Exception:
                    pass
            self.agents.clear()

    def active_count(self) -> int:
        """Return the number of currently active agents."""
        with self._lock:
            return sum(1 for a in self.agents.values() if a.is_running())

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
        return False


# Convenience function for one-off executions
def run_pi_once(
    prompt: str,
    model: str = "claude-sonnet-4-5",
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Execute a single prompt with pi and return the result.

    This is a convenience function for one-off executions that don't
    need persistent connections.

    Args:
        prompt: The task/prompt to execute
        model: AI model to use
        cwd: Working directory
        timeout: Maximum execution time in seconds

    Returns:
        Tuple of (response_text, error_message)
    """
    with PiRPCClient(model=model, cwd=cwd) as client:
        return client.execute(prompt, timeout=timeout)
