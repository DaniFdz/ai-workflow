#!/usr/bin/env python3
"""
MiniDani - Competitive parallel AI development system
Runs 3 AI coding agents in parallel, judges selects best implementation
"""

import subprocess, json, time, threading, sys, signal, os, shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, IO, cast

from pi_client import PiRPCClient, PiAgentPool


@dataclass
class ManagerState:
    id: str
    status: str = "pending"
    worktree: Optional[Path] = None
    branch: Optional[str] = None
    score: Optional[int] = None
    summary: Optional[str] = None
    round: int = 1
    start_time: Optional[float] = None
    last_log: str = ""
    last_log_at: Optional[float] = None


@dataclass
class SystemState:
    prompt: str
    repo_path: Path
    branch_base: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    current_round: int = 1
    managers: Dict[str, ManagerState] = field(default_factory=dict)
    winner: Optional[str] = None
    pr_url: Optional[str] = None


class MiniDani:
    QUALITY_THRESHOLD = 80
    MANAGER_TIMEOUT = 7200  # 2 hours

    def __init__(
        self,
        repo_path: Path,
        user_prompt: str,
        branch_prefix: str = "",
        branch_name: str = "",
        no_pr: bool = False,
    ):
        self.repo_path = repo_path
        self.user_prompt = user_prompt
        self.branch_prefix = branch_prefix
        self.branch_name = branch_name
        self.no_pr = no_pr
        self.lock = threading.Lock()
        self._progress_len = 0

        # Check for pi coding agent
        self.pi = shutil.which("pi")
        if not self.pi:
            raise FileNotFoundError(
                "Pi coding agent not found. Install: npm install -g @mariozechner/pi-coding-agent"
            )

        # Initialize agent pool for parallel execution
        # 3 managers × 2 teams (blue/red) = 6 potential concurrent agents
        self.agent_pool = PiAgentPool(size=6, model="claude-sonnet-4-5")

        self.state = SystemState(
            prompt=user_prompt,
            repo_path=repo_path,
            managers={
                "a": ManagerState("a"),
                "b": ManagerState("b"),
                "c": ManagerState("c"),
            },
        )

    def log(self, msg: str, mgr: str = "Sys", lvl: str = "LOG"):
        colors = {
            "DEBUG": "\033[90m",  # Gray
            "LOG": "\033[0m",  # Default
            "INFO": "\033[36m",  # Cyan
            "SUCCESS": "\033[32m",  # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",  # Red
        }
        reset = "\033[0m"
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = colors.get(lvl, "\033[0m")
        with self.lock:
            if sys.stdout.isatty() and self._progress_len > 0:
                sys.stdout.write("\r" + (" " * self._progress_len) + "\r")
                self._progress_len = 0
            print(f"{color}[{timestamp}] [{lvl:7s}] [{mgr:8s}] {msg}{reset}")

    def run_pi(
        self,
        prompt: str,
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        agent: Optional[str] = None,
        log_prefix: str = "Pi",
    ):
        """
        Run pi coding agent with specified prompt. Returns (result, error_msg).

        This method uses the pi RPC client to execute prompts. The agent parameter
        is used for logging purposes (pi doesn't have separate agent configs like OpenCode).

        Args:
            prompt: The task/prompt to send to pi
            cwd: Working directory for execution
            timeout: Maximum execution time in seconds
            agent: Agent name for logging (e.g., "manager", "judge")
            log_prefix: Prefix for log messages

        Returns:
            Tuple of ({"response": text}, None) on success
            Tuple of (None, error_message) on failure
        """
        try:
            self.log(f"Starting {agent or 'pi'}", mgr=log_prefix, lvl="INFO")

            start = time.time()

            # Create a dedicated client for this execution
            # Using cwd to ensure pi runs in the correct directory
            client = PiRPCClient(model="claude-sonnet-4-5", cwd=cwd or self.repo_path)

            if not client.start():
                return None, "Failed to start pi process"

            try:
                # Track last chunk for progress updates
                def on_chunk(chunk: str):
                    if log_prefix.startswith("M"):
                        mid = log_prefix[-1].lower()
                        if mid in self.state.managers:
                            self.state.managers[mid].last_log = chunk[-200:]
                            self.state.managers[mid].last_log_at = time.time()

                # Execute the prompt
                response_text, error = client.execute(
                    prompt, timeout=timeout, on_chunk=on_chunk
                )

                elapsed = time.time() - start
                self.log(f"Completed in {elapsed:.1f}s", mgr=log_prefix, lvl="INFO")

                if response_text:
                    return {"response": response_text}, None
                else:
                    return None, error or "No response received"

            finally:
                # Always clean up the client
                client.stop()

        except Exception as e:
            return None, str(e)

    def generate_branch_name(self) -> str:
        """Generate branch name using OpenAI API or manual input"""
        if self.branch_name:
            return self.branch_name

        self.log("Generating branch name with OpenAI...", lvl="DEBUG")
        try:
            script = Path(__file__).parent / "generate_branch_name.py"
            result = subprocess.run(
                ["python3", str(script), self.user_prompt[:500]],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                # Parse JSON response: {"branch_name": "..."}
                data = json.loads(result.stdout.strip())
                branch = data.get("branch_name", "").strip()
                if branch:
                    return branch
        except json.JSONDecodeError as e:
            self.log(f"Branch JSON parse failed: {e}", lvl="WARNING")
        except Exception as e:
            self.log(f"Branch generation failed: {e}", lvl="WARNING")

        # Fallback: simple slug from prompt
        import re

        slug = re.sub(r"[^a-z0-9]+", "-", self.user_prompt[:50].lower()).strip("-")
        return slug[:30] or "feature"

    def p1_branch(self):
        """Phase 1: Generate and set branch name"""
        self.log("Determining branch name")
        base = self.generate_branch_name()
        self.state.branch_base = (
            f"{self.branch_prefix}{base}" if self.branch_prefix else base
        )
        self.log(f"Branch: {self.state.branch_base}", lvl="SUCCESS")

    def p2_setup(self, round_num: int):
        """Phase 2: Create worktrees for each manager"""
        self.log(f"Setting up worktrees (Round {round_num})")

        for mid, mg in self.state.managers.items():
            # Clean up existing worktree if present
            if mg.worktree and mg.worktree.exists():
                subprocess.run(
                    ["git", "worktree", "remove", str(mg.worktree), "--force"],
                    cwd=self.repo_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            # Create worktree
            suffix = self.state.branch_base.split("/")[-1]
            wt = (
                self.repo_path.parent
                / f"{self.repo_path.name}_{suffix}_r{round_num}_{mid}"
            )
            br = f"{self.state.branch_base}-r{round_num}-{mid}"

            subprocess.run(
                ["git", "branch", "-D", br],
                cwd=self.repo_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            result = subprocess.run(
                ["git", "worktree", "add", str(wt), "-b", br],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise Exception(
                    f"Failed to create worktree for {mid}: {result.stderr[:200]}"
                )

            mg.worktree, mg.branch, mg.round = wt, br, round_num
            mg.status, mg.score = "pending", None
            self.log(f"Worktree {mid.upper()} ready", lvl="SUCCESS")

    def run_manager(self, mid: str, round_num: int):
        """Run a single manager"""
        m = self.state.managers[mid]
        m.status = "running"
        m.start_time = time.time()
        m.last_log = ""
        m.last_log_at = None
        self.log(f"Start R{round_num}", mgr=f"M{mid.upper()}", lvl="LOG")

        feedback = ""
        if round_num > 1:
            feedback = "\n\nIMPORTANT: Previous round had low quality. Focus on complete implementation, tests, docs, error handling."

        try:
            r, error = self.run_pi(
                f"User task:\n{self.user_prompt}{feedback}",
                m.worktree,
                timeout=self.MANAGER_TIMEOUT,
                agent="manager",
                log_prefix=f"M{mid.upper()}",
            )
            if r:
                m.summary = r.get("response", "")[:500]
                m.status = "complete"
                self.log(f"OK R{round_num}", mgr=f"M{mid.upper()}", lvl="SUCCESS")
            else:
                m.status = "failed"
                self.log(
                    f"Failed: {error[:100] if error else 'unknown'}",
                    mgr=f"M{mid.upper()}",
                    lvl="ERROR",
                )
        except Exception as e:
            m.status = "failed"
            self.log(f"Error: {e}", mgr=f"M{mid.upper()}", lvl="ERROR")

    def p3_managers(self, round_num: int):
        """Phase 3: Run all managers in parallel"""
        self.log(f"Running 3 managers (Round {round_num})")

        stop_event = threading.Event()

        def progress_loop():
            if not sys.stdout.isatty():
                while not stop_event.is_set():
                    time.sleep(10)
                    lines = []
                    for mid in ["a", "b", "c"]:
                        m = self.state.managers[mid]
                        if m.status == "running" and m.start_time:
                            elapsed = time.time() - m.start_time
                            last = f" | last: {m.last_log}" if m.last_log else ""
                            lines.append(f"{mid.upper()} {elapsed:.0f}s{last}")
                    if lines:
                        self.log("Progress: " + "; ".join(lines), lvl="INFO")
                return

            last_len = 0
            spinner = ["-", "\\", "|", "/"]
            while not stop_event.is_set():
                now = time.time()
                parts = []
                logs = []
                earliest_start = None
                for mid in ["a", "b", "c"]:
                    m = self.state.managers[mid]
                    if m.status == "running" and m.start_time:
                        if earliest_start is None or m.start_time < earliest_start:
                            earliest_start = m.start_time
                        elapsed = now - m.start_time
                        bar_total = self.MANAGER_TIMEOUT or 1
                        fill = int(min(elapsed / bar_total, 1.0) * 10)
                        bar = "#" * fill + "." * (10 - fill)
                        spin = spinner[int(now * 4) % len(spinner)]
                        parts.append(f"{mid.upper()} {spin} [{bar}] {elapsed:.0f}s")
                        if m.last_log:
                            logs.append(f"{mid.upper()}: {m.last_log}")
                    elif m.status == "complete":
                        parts.append(f"{mid.upper()} [##########] done")
                        if m.last_log:
                            logs.append(f"{mid.upper()}: {m.last_log}")
                    elif m.status == "failed":
                        parts.append(f"{mid.upper()} [!!!!!!!!!!] fail")
                        if m.last_log:
                            logs.append(f"{mid.upper()}: {m.last_log}")

                total_elapsed = 0.0
                if earliest_start is not None:
                    total_elapsed = now - earliest_start

                log_text = " | logs " + " | ".join(logs) if logs else ""
                line = " ".join(parts) + f" | total {total_elapsed:.0f}s" + log_text

                with self.lock:
                    pad = " " * max(0, last_len - len(line))
                    sys.stdout.write("\r" + line + pad)
                    sys.stdout.flush()
                    last_len = len(line)
                    self._progress_len = last_len

                time.sleep(1)

            with self.lock:
                if last_len:
                    sys.stdout.write("\r" + (" " * last_len) + "\r")
                    sys.stdout.flush()
                    self._progress_len = 0

        threads = []
        for mid in ["a", "b", "c"]:
            t = threading.Thread(target=self.run_manager, args=(mid, round_num))
            t.start()
            threads.append(t)

        progress_thread = threading.Thread(target=progress_loop, daemon=True)
        progress_thread.start()

        for t in threads:
            t.join()

        stop_event.set()

        complete = sum(
            1 for m in self.state.managers.values() if m.status == "complete"
        )
        self.log(
            f"Managers done: {complete}/3 complete",
            lvl="SUCCESS" if complete > 0 else "WARNING",
        )

    def p4_judge(self, round_num: int) -> Dict[str, int]:
        """Phase 4: Judge evaluates all implementations"""
        self.log(f"Judging Round {round_num}", lvl="INFO")

        summaries = "\n\n".join(
            [
                f"Manager {mid.upper()} Summary: {m.summary or '(no output)'}"
                for mid, m in self.state.managers.items()
            ]
        )

        judge_prompt = f"""Original task: {self.user_prompt}

{summaries}

Evaluate each implementation (A, B, C) and provide JSON:
{{"scores": {{"A": 0-100, "B": 0-100, "C": 0-100}}, "winner": "A"|"B"|"C", "reasoning": "..."}}

Criteria: Completeness (35%), Code Quality (30%), Correctness (25%), Best Practices (10%)"""

        r, error = self.run_pi(
            judge_prompt, self.repo_path, agent="judge", log_prefix="Judge"
        )

        scores = {"a": 0, "b": 0, "c": 0}
        winner = "a"

        if r:
            response = r.get("response", "")
            try:
                # Extract JSON from response
                import re

                json_match = re.search(
                    r'\{[^{}]*"scores"[^{}]*\{[^{}]*\}[^{}]*\}', response, re.DOTALL
                )
                if json_match:
                    data = json.loads(json_match.group())
                    for k, v in data.get("scores", {}).items():
                        scores[k.lower()] = int(v) if isinstance(v, (int, float)) else 0
                    winner = data.get("winner", "a").lower()
            except:
                pass

        # Update state
        for mid, score in scores.items():
            self.state.managers[mid].score = score
        self.state.winner = winner

        self.log(
            f"Scores: A={scores['a']}, B={scores['b']}, C={scores['c']}", lvl="INFO"
        )
        self.log(f"Winner: {winner.upper()}", lvl="SUCCESS")

        return scores

    def p5_cleanup(self):
        """Phase 5: Remove losing worktrees"""
        self.log("Cleaning up losers")

        for mid, mg in self.state.managers.items():
            if mid != self.state.winner and mg.worktree and mg.worktree.exists():
                subprocess.run(
                    ["git", "worktree", "remove", str(mg.worktree), "--force"],
                    cwd=self.repo_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if mg.branch:
                    subprocess.run(
                        ["git", "branch", "-D", mg.branch],
                        cwd=self.repo_path,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                self.log(f"Removed {mid.upper()}", lvl="SUCCESS")

    def p6_pr(self):
        """Phase 6: Create PR or commit locally"""
        if not self.state.winner:
            raise RuntimeError("Winner not set")

        w = self.state.managers[self.state.winner]
        if not w.worktree:
            raise RuntimeError("Winner worktree missing")

        self.log(f"Winner: {self.state.winner.upper()}, Score: {w.score}")

        if self.no_pr:
            self.log("Committing to original repo (--no-pr mode)")
            prompt = f"""Original task: {self.user_prompt}

Winning implementation: Manager {self.state.winner.upper()} (Score: {w.score}/100)
Summary: {w.summary}

Your job:
1. Check what files were created/modified (git status)
2. Stage ONLY production-relevant files - exclude .opencode/, plan.md, logs, __pycache__, etc.
3. Commit with a clear message

IMPORTANT: Do NOT push or create a PR. Only stage and commit locally."""
        else:
            self.log("Creating PR")
            prompt = f"""Original task: {self.user_prompt}

Winning implementation: Manager {self.state.winner.upper()} (Score: {w.score}/100)
Summary: {w.summary}

Your job:
1. Check what files were created/modified (git status)
2. Stage ONLY production-relevant files - exclude .opencode/, plan.md, logs, __pycache__, etc.
3. Commit with a clear message
4. Push the branch to origin
5. Create a Pull Request using `gh pr create`

Output the PR URL at the end."""

        r, error = self.run_pi(prompt, w.worktree, agent="pr-creator", log_prefix="PR")

        if r and not self.no_pr:
            import re

            pr_match = re.search(
                r"https://github\.com/[^\s]+/pull/\d+", r.get("response", "")
            )
            if pr_match:
                self.state.pr_url = pr_match.group(0)
                self.log(f"PR created: {self.state.pr_url}", lvl="SUCCESS")
        elif r and self.no_pr:
            # Copy changes to original repo
            try:
                diff = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                    cwd=w.worktree,
                    capture_output=True,
                    text=True,
                )
                files = [
                    f.strip() for f in diff.stdout.strip().split("\n") if f.strip()
                ]

                for f in files:
                    src, dst = w.worktree / f, self.repo_path / f
                    if src.exists():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)

                if files:
                    subprocess.run(["git", "add"] + files, cwd=self.repo_path)
                    msg = f"feat: {self.state.branch_base}\n\nBy Manager {self.state.winner.upper()} (Score: {w.score}/100)"
                    subprocess.run(["git", "commit", "-m", msg], cwd=self.repo_path)
                    self.log("Committed to original repo", lvl="SUCCESS")
            except Exception as e:
                self.log(f"Error copying changes: {e}", lvl="ERROR")
        elif error:
            self.log(f"PR creation failed: {error[:200]}", lvl="ERROR")

    def cleanup_all_worktrees(self):
        """Clean up all worktrees created by this session and pi processes"""
        # First, clean up all pi agent processes to prevent zombies
        self.agent_pool.cleanup()

        self.log("Cleaning up all worktrees")
        for mid, mg in self.state.managers.items():
            if mg.worktree and mg.worktree.exists():
                try:
                    subprocess.run(
                        ["git", "worktree", "remove", str(mg.worktree), "--force"],
                        cwd=self.repo_path,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except:
                    pass
            if mg.branch:
                subprocess.run(
                    ["git", "branch", "-D", mg.branch],
                    cwd=self.repo_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.repo_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def check_quality(self, scores: Dict[str, int]) -> bool:
        """Returns True if all scores are below threshold (needs retry)"""
        return all(s < self.QUALITY_THRESHOLD for s in scores.values() if s > 0)

    def run(self):
        """Main execution"""

        def signal_handler(sig, frame):
            self.log("Ctrl+C detected, cleaning up...", lvl="WARNING")
            self.cleanup_all_worktrees()
            sys.exit(1)

        signal.signal(signal.SIGINT, signal_handler)

        try:
            self.log("MiniDani Starting...")
            subprocess.run(
                ["git", "worktree", "prune"],
                cwd=self.repo_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Phase 1: Branch
            self.p1_branch()

            # Round 1
            self.state.current_round = 1
            self.p2_setup(1)
            self.p3_managers(1)
            scores_r1 = self.p4_judge(1)

            # Retry if needed
            if self.check_quality(scores_r1):
                self.log("All scores < 80. Starting Round 2...", lvl="WARNING")
                self.state.current_round = 2
                self.state.winner = None
                self.p2_setup(2)
                self.p3_managers(2)
                self.p4_judge(2)

            if not self.state.winner:
                self.log("No winner selected; aborting cleanup/PR", lvl="ERROR")
                return {"success": False, "error": "No winner selected"}

            # Cleanup and PR
            self.p5_cleanup()
            self.p6_pr()

            elapsed = (datetime.now() - self.state.start_time).total_seconds()
            self.log(f"Done in {elapsed:.1f}s", lvl="SUCCESS")

            return {
                "success": True,
                "winner": self.state.winner,
                "branch": self.state.managers[self.state.winner].branch,
                "round": self.state.managers[self.state.winner].round,
                "scores": {m: self.state.managers[m].score for m in ["a", "b", "c"]},
                "elapsed": elapsed,
                "pr_url": self.state.pr_url,
            }
        except Exception as e:
            self.log(f"Fatal: {e}", lvl="ERROR")
            return {"success": False, "error": str(e)}
        finally:
            self.cleanup_all_worktrees()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="MiniDani - Competitive AI development system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  minidani "Create a REST API"                    # Inline prompt
  minidani -f prompt.md                           # From file
  cat prompt.md | minidani                        # From stdin
  minidani -b my-branch "Add feature"             # Custom branch name
  minidani --branch-prefix "feat/" "Add auth"    # With prefix
  minidani -n "Refactor utils"                    # Commit locally, no PR
        """,
    )

    parser.add_argument("prompt", nargs="*", help="Task prompt")
    parser.add_argument("-f", "--file", type=Path, help="Read prompt from file")
    parser.add_argument(
        "--branch-prefix", type=str, default=None, help="Branch prefix (e.g., 'feat/')"
    )
    parser.add_argument(
        "-b", "--branch-name", type=str, default=None, help="Manual branch name"
    )
    parser.add_argument(
        "-n",
        "--no-pr",
        action="store_true",
        help="Commit locally instead of creating PR",
    )

    args = parser.parse_args()

    # Determine prompt
    prompt = None
    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        prompt = args.file.read_text().strip()
    elif args.prompt:
        prompt = " ".join(args.prompt)
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(1)

    if not prompt:
        print("Error: Empty prompt")
        sys.exit(1)

    # Branch prefix
    branch_prefix = args.branch_prefix or os.getenv("BRANCH_PREFIX", "")
    if branch_prefix and not branch_prefix.endswith("/"):
        branch_prefix += "/"

    # Run
    minidani = MiniDani(
        Path.cwd(),
        prompt,
        branch_prefix=branch_prefix,
        branch_name=args.branch_name or "",
        no_pr=args.no_pr,
    )
    result = minidani.run()

    print("\n" + "=" * 70)
    print("RESULT:", json.dumps(result, indent=2))
