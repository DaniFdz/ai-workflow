#!/usr/bin/env python3
"""
Pi Coding Agent Client - Print Mode Implementation

Uses pi's --print mode for non-interactive execution.
"""

import subprocess
import time
import shutil
from pathlib import Path
from typing import Optional, Tuple


class PiRPCClient:
    """Client for pi coding agent using --print mode."""
    
    def __init__(self, model: str = "claude-sonnet-4-5", cwd: Optional[Path] = None):
        self.model = model
        self.cwd = cwd or Path.cwd()
        self.pi_path = self._find_pi()
        
    def _find_pi(self) -> Optional[str]:
        """Find pi executable."""
        pi = shutil.which("pi")
        if pi:
            return pi
        
        npm_global = Path.home() / ".npm-global" / "bin" / "pi"
        if npm_global.exists():
            return str(npm_global)
        
        return None
        
    def start(self) -> bool:
        """Check if pi is available (no persistent process needed)."""
        return self.pi_path is not None
    
    def execute(self, prompt: str, timeout: Optional[int] = None, on_chunk=None) -> Tuple[Optional[str], Optional[str]]:
        """
        Execute a prompt using pi's --print mode.
        
        Args:
            prompt: The task to execute
            timeout: Maximum execution time in seconds
            on_chunk: Callback for streaming (not used in print mode)
            
        Returns:
            (response_text, None) on success
            (None, error_message) on failure
        """
        if not self.pi_path:
            return None, "Pi executable not found"
        
        try:
            # Build command
            cmd = [
                self.pi_path,
                "--print",  # Non-interactive mode
                "--model", self.model,
                prompt
            ]
            
            # Execute
            result = subprocess.run(
                cmd,
                cwd=str(self.cwd),
                capture_output=True,
                text=True,
                timeout=timeout or 1800,  # 30 min default
            )
            
            if result.returncode == 0:
                return result.stdout or "Task completed", None
            else:
                error_msg = result.stderr or f"Process exited with code {result.returncode}"
                return None, error_msg
                
        except subprocess.TimeoutExpired:
            return None, f"Timeout after {timeout}s"
        except Exception as e:
            return None, str(e)
    
    def stop(self):
        """No-op in print mode (no persistent process)."""
        pass
    
    def is_running(self) -> bool:
        """Always False in print mode."""
        return False


# Compatibility class
class PiAgentPool:
    """Dummy pool for compatibility."""
    def __init__(self, size: int = 3, model: str = "claude-sonnet-4-5"):
        pass
    
    def cleanup(self):
        """No-op cleanup."""
        pass
