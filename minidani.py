#!/usr/bin/env python3
"""
MiniDani with Retry Logic - If all scores < 80, launch second round
"""

import subprocess, json, time, threading, sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.table import Table
from rich.text import Text

@dataclass
class ManagerState:
    id: str
    status: str = "pending"
    iteration: int = 0
    phase: str = ""
    last_activity: str = ""
    worktree: Optional[Path] = None
    branch: Optional[str] = None
    score: Optional[int] = None
    summary: Optional[str] = None
    round: int = 1  # NEW: Track which round

@dataclass
class SystemState:
    prompt: str
    repo_path: Path
    branch_base: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    current_phase: int = 0
    current_round: int = 1  # NEW: Track rounds
    phase_progress: Dict[int, float] = field(default_factory=lambda: {i: 0.0 for i in range(6)})
    managers: Dict[str, ManagerState] = field(default_factory=dict)
    activity_log: List[tuple] = field(default_factory=list)
    winner: Optional[str] = None

class MiniDaniRetry:
    def __init__(self, repo_path: Path, user_prompt: str, branch_prefix: str = "", debug: bool = False):
        self.repo_path, self.user_prompt = repo_path, user_prompt
        self.branch_prefix = branch_prefix
        self.debug = debug
        self.debug_logs = []  # Accumulate debug logs here
        self.opencode = Path.home() / ".opencode" / "bin" / "opencode"
        self.console, self.lock = Console(), threading.Lock()
        if not self.opencode.exists(): raise FileNotFoundError("OpenCode not found")
        self.state = SystemState(
            prompt=user_prompt, 
            repo_path=repo_path, 
            managers={
                "a": ManagerState("a"), 
                "b": ManagerState("b"), 
                "c": ManagerState("c")
            }
        )
        self.phase_names = ["Branch", "Setup", "Managers", "Judge", "Cleanup", "PR"]
        self.QUALITY_THRESHOLD = 80  # If all < 80, retry
    
    def log(self, msg: str, mgr: str = "Sys", lvl: str = "INFO"):
        icons = {"SUCCESS":"✅", "WORKING":"🔄", "JUDGE":"⚖️", "WINNER":"🏆", "WARNING":"⚠️", "INFO":"ℹ️", "ERROR":"❌"}
        with self.lock: 
            self.state.activity_log.append((datetime.now(), mgr, f"{icons.get(lvl,'ℹ️')} {msg}"))
            
            # Also log to debug buffer if debug mode enabled
            if self.debug:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                self.debug_logs.append(f"[{timestamp}] [{mgr:8s}] [{lvl:7s}] {msg}")
    
    def make_layout(self):
        layout = Layout()
        layout.split(Layout(name="header", size=5), Layout(name="body"), Layout(name="footer", size=2))
        layout["body"].split_row(Layout(name="left"), Layout(name="right", ratio=2))
        layout["right"].split(Layout(name="managers", ratio=2), Layout(name="activity"))
        return layout
    
    def render_header(self):
        el = str(datetime.now() - self.state.start_time).split('.')[0]
        round_text = f" [Round {self.state.current_round}]" if self.state.current_round > 1 else ""
        return Panel(
            Text(f"🦞 MiniDani{round_text}\n{self.state.branch_base or 'Init...'} | {el}", style="bold cyan"), 
            border_style="blue"
        )
    
    def render_phases(self):
        prog = Progress(SpinnerColumn(), TextColumn("[bold]{task.description}"), BarColumn(), TextColumn("{task.percentage:>3.0f}%"))
        for i, n in enumerate(self.phase_names):
            p = self.state.phase_progress.get(i, 0)
            icon = "✅" if p>=100 else "🔄" if i==self.state.current_phase else "⏳"
            prog.add_task(f"{icon} {i+1}. {n}", total=100, completed=p)
        return Panel(prog, title="Phases", border_style="green")
    
    def render_managers(self):
        t = Table(show_header=False, box=None, padding=(0,1))
        for mid, m in self.state.managers.items():
            ic, st = ("✅","green") if m.status=="complete" else ("🔄","yellow") if m.status=="running" else ("❌","red") if m.status=="failed" else ("⏳","dim")
            
            round_badge = f"R{m.round}" if m.round > 1 else ""
            t.add_row(Text(f"🤖 Manager {mid.upper()} {round_badge}", style="bold cyan"))
            
            status_line = f"   {ic} {m.status.title()}"
            if m.iteration>0: status_line += f" (i{m.iteration})"
            t.add_row(Text(status_line, style=st))
            
            if m.phase: t.add_row(Text(f"   {m.phase}", style="dim"))
            if m.last_activity: t.add_row(Text(f"   {m.last_activity[:45]}", style="dim italic"))
            
            if m.score is not None:
                score_style = "bold green" if m.score>=90 else "yellow" if m.score>=80 else "red"
                score_icon = "🏆" if self.state.winner==mid else ""
                t.add_row(Text(f"   {score_icon}Score: {m.score}/100", style=score_style))
            
            t.add_row("")
        return Panel(t, title=f"Managers (Round {self.state.current_round})", border_style="cyan")
    
    def render_activity(self):
        t = Table(show_header=False, box=None, padding=0)
        for ts, mg, ms in self.state.activity_log[-8:]:
            st = "green" if "✅" in ms else "red" if "❌" in ms else "bold green" if "🏆" in ms else "yellow" if "⚠️" in ms else "white"
            t.add_row(Text(f"{ts.strftime('%H:%M:%S')} [{mg[:8]}] {ms[:50]}", style=st))
        return Panel(t, title="Activity", border_style="magenta", height=11)
    
    def render(self, layout):
        layout["header"].update(self.render_header())
        layout["left"].update(self.render_phases())
        layout["managers"].update(self.render_managers())
        layout["right"]["activity"].update(self.render_activity())
        
        footer_text = f"🏆 Winner: {self.state.winner.upper()}" if self.state.winner else "Running..."
        layout["footer"].update(Panel(Text(footer_text, style="bold green" if self.state.winner else "dim"), border_style="dim"))
    
    def get_input_with_timeout(self, prompt_text, timeout_sec):
        """Get user input with timeout. Returns (input_str, timed_out)"""
        import select
        
        print(f"\n{prompt_text}", flush=True)
        print(f"(Auto-accept in {timeout_sec}s if no response)", flush=True)
        
        # Check if input is available (Unix only)
        if hasattr(select, 'select'):
            ready, _, _ = select.select([sys.stdin], [], [], timeout_sec)
            if ready:
                return sys.stdin.readline().strip(), False
            else:
                return "", True
        else:
            # Fallback for Windows - no timeout support
            return input().strip(), False
    
    def run_oc(self, p, c=None, t=300, agent=None, model=None):
        """Run OpenCode with optional agent system prompt. Returns (result, error_msg)"""
        try:
            # If agent is specified, prepend agent instructions to prompt
            if agent:
                agent_path = Path(__file__).parent / ".opencode" / "agents" / f"{agent}.md"
                if agent_path.exists():
                    agent_prompt = agent_path.read_text()
                    p = f"{agent_prompt}\n\n---\n\n{p}"
            
            # Build command: opencode run --format json --model <model> [--session <id>] <prompt>
            # Use provided model or default to claude-sonnet-4
            model = model or "anthropic/claude-sonnet-4"
            cmd = [str(self.opencode), "run", "--format", "json", "--model", model]
            if c:
                cmd.extend(["--session", str(c)])
            cmd.append(p)
            
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=t)
            
            if r.returncode == 0:
                return json.loads(r.stdout), None
            else:
                # Capture error information
                error_msg = f"Exit code {r.returncode}"
                if r.stderr:
                    error_msg += f"\nStderr: {r.stderr[:500]}"  # First 500 chars
                if r.stdout:
                    error_msg += f"\nStdout: {r.stdout[:500]}"
                return None, error_msg
        except subprocess.TimeoutExpired:
            return None, f"Timeout after {t}s"
        except Exception as e:
            return None, f"Exception: {str(e)}"
    
    def p1_branch(self):
        if self.state.branch_base:  # Already have branch from round 1
            return
        self.log("Gen branch"); self.state.current_phase=0
        
        # Ask branch-namer agent to generate with configured prefix
        if self.branch_prefix:
            prompt = f"""Branch prefix to use: {self.branch_prefix}
Task description: {self.user_prompt}

Generate a branch name using the prefix '{self.branch_prefix}' followed by a concise description."""
        else:
            prompt = f"""No prefix required - generate simple branch name.
Task description: {self.user_prompt}

Generate a concise branch name (no prefix, just description in kebab-case)."""
        
        # Use fast model (gpt-4o-mini) with short timeout for simple branch naming
        r, error = self.run_oc(prompt, self.repo_path, t=30, agent="branch-namer", model="openai/gpt-4o-mini")
        bn = f"{self.branch_prefix}task"  # Fallback
        
        if r:
            response_text = r.get("response", "")
            for line in response_text.split("\n"):
                line = line.strip()
                # Accept any line that starts with the configured prefix
                if line.startswith(self.branch_prefix) and len(line) < 50:
                    bn = line
                    break
        elif error and self.debug:
            self.log(f"Branch namer failed: {error[:100]}", lvl="ERROR")
        
        # Pause TUI for user confirmation
        print("\n" + "="*70)
        print(f"🌿 Proposed branch name: {bn}")
        if self.branch_prefix:
            print(f"   (using prefix: {self.branch_prefix})")
        else:
            print(f"   (no prefix configured)")
        print("="*70)
        
        response, timed_out = self.get_input_with_timeout(
            "Approve? [Y/n/custom name]: ",
            timeout_sec=20
        )
        
        if timed_out:
            print("⏱️  Timeout - auto-accepting branch name")
            self.log(f"Branch (auto): {bn}", lvl="SUCCESS")
        elif response.lower() in ['', 'y', 'yes']:
            print("✅ Branch name approved")
            self.log(f"Branch (approved): {bn}", lvl="SUCCESS")
        elif response.lower() in ['n', 'no']:
            # Prompt for custom name
            example = f"{self.branch_prefix}my-feature" if self.branch_prefix else "my-custom-branch"
            print(f"Enter custom branch name (e.g., {example}): ", end='', flush=True)
            custom = sys.stdin.readline().strip()
            if self._validate_branch_name(custom):
                bn = custom
                print(f"✅ Using custom branch: {bn}")
                self.log(f"Branch (custom): {bn}", lvl="SUCCESS")
            else:
                print(f"⚠️  Invalid format (spaces/special chars not allowed), using original: {bn}")
                self.log(f"Branch (fallback): {bn}", lvl="WARNING")
        else:
            # User typed something else - treat as custom branch name
            if self._validate_branch_name(response):
                bn = response
                print(f"✅ Using custom branch: {bn}")
                self.log(f"Branch (custom): {bn}", lvl="SUCCESS")
            else:
                print(f"⚠️  Invalid format '{response}' (spaces/special chars not allowed), using original: {bn}")
                self.log(f"Branch (fallback): {bn}", lvl="WARNING")
        
        print("="*70 + "\n")
        self.state.branch_base = bn
        self.state.phase_progress[0]=100
        time.sleep(1)  # Brief pause before resuming TUI
    
    def _validate_branch_name(self, name: str) -> bool:
        """Validate branch name - allow any format without spaces or special chars"""
        if not name or len(name) > 100:
            return False
        # Git branch names can't have spaces, ~, ^, :, ?, *, [, \
        invalid_chars = [' ', '~', '^', ':', '?', '*', '[', '\\', '..']
        return not any(char in name for char in invalid_chars)
    
    def print_debug_logs(self):
        """Print accumulated debug logs at the end of execution"""
        if not self.debug or not self.debug_logs:
            return
        
        print("\n" + "="*80)
        print("DEBUG LOGS".center(80))
        print("="*80)
        
        for log_line in self.debug_logs:
            print(log_line)
        
        print("="*80)
        print(f"Total debug entries: {len(self.debug_logs)}")
        print("="*80 + "\n")
    
    def p2_setup(self, round_num: int):
        self.log(f"Setup worktrees (Round {round_num})"); self.state.current_phase=1
        
        # Extract suffix from branch_base (part after last /)
        # Examples: "feat/auth" → "auth", "auth" → "auth"
        suffix = self.state.branch_base.split('/')[-1] if '/' in self.state.branch_base else self.state.branch_base
        
        # Cleanup previous round if any
        for i, m in enumerate(["a","b","c"]):
            mg = self.state.managers[m]
            if mg.worktree and mg.worktree.exists():
                subprocess.run(["git","worktree","remove",str(mg.worktree),"--force"], 
                             cwd=self.repo_path, stderr=subprocess.DEVNULL)
                if mg.branch:
                    subprocess.run(["git","branch","-D",str(mg.branch)], 
                                 cwd=self.repo_path, stderr=subprocess.DEVNULL)
            
            # Create new worktree
            # Branch name includes full path: prefix/suffix-r1-a or suffix-r1-a
            br = f"{self.state.branch_base}-r{round_num}-{m}"
            
            # Worktree folder uses only suffix (no prefix): reponame_suffix_r1_a
            wt = self.repo_path.parent / f"{self.repo_path.name}_{suffix}_r{round_num}_{m}"
            
            subprocess.run(["git","worktree","add",str(wt),"-b",br], 
                         cwd=self.repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            mg.worktree, mg.branch, mg.round = wt, br, round_num
            mg.status, mg.score, mg.iteration = "pending", None, 0  # Reset
            
            self.log(f"WT {m.upper()} R{round_num}", lvl="SUCCESS")
            self.state.phase_progress[1]=((i+1)/3)*100
    
    def rm(self, mid, round_num):
        m = self.state.managers[mid]; m.status="running"
        self.log(f"Start R{round_num}", mgr=f"M{mid.upper()}", lvl="WORKING")
        
        # Add feedback from previous round if it was low quality
        feedback = ""
        if round_num > 1:
            feedback = "\n\nIMPORTANT: Previous round had low quality scores. Focus on:\n- Complete implementation\n- Comprehensive tests\n- Good documentation\n- Error handling\n- Code quality"
        
        try:
            m.phase, m.last_activity, m.iteration = "Impl", "Working...", 1
            # Timeout: 20 min base + 10 min per iteration (30 min for iteration 1)
            r, error = self.run_oc(f"User task:\n{self.user_prompt}{feedback}", 
                          m.worktree, t=1800, agent="manager")
            if r:
                m.summary, m.status, m.last_activity = r.get("response","")[:500], "complete", "Done"
                subprocess.run(["git","add","."], cwd=m.worktree)
                subprocess.run(["git","commit","-m",f"feat: r{round_num} {mid}"], 
                             cwd=m.worktree, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.log(f"OK R{round_num}", mgr=f"M{mid.upper()}", lvl="SUCCESS")
            else:
                m.status, m.last_activity = "failed", "Failed"
                self.log(f"Fail R{round_num}", mgr=f"M{mid.upper()}", lvl="ERROR")
                if error:
                    # Log detailed error in debug mode
                    self.log(f"Error details: {error}", mgr=f"M{mid.upper()}", lvl="ERROR")
        except Exception as e:
            m.status, m.last_activity = "failed", str(e)[:30]
            self.log(f"Err R{round_num}:{e}", mgr=f"M{mid.upper()}", lvl="ERROR")
    
    def p3_managers(self, round_num):
        self.log(f"3 managers (Round {round_num})"); self.state.current_phase=2
        ts = [threading.Thread(target=self.rm, args=(m, round_num)) for m in ["a","b","c"]]
        for t in ts: t.start()
        st = time.time()
        while any(t.is_alive() for t in ts):
            time.sleep(2)
            self.state.phase_progress[2]=(sum(1 for m in self.state.managers.values() if m.status=="complete")/3)*100
            if time.time()-st>900: break
        for t in ts: t.join(1)
        self.state.phase_progress[2]=100
        self.log(f"All done R{round_num}", lvl="SUCCESS")
    
    def p4_judge(self, round_num):
        self.log(f"Judging R{round_num}", lvl="JUDGE"); self.state.current_phase=3
        sums = [f"M{m.upper()}: {self.state.managers[m].summary[:150] if self.state.managers[m].status=='complete' else 'FAIL'}" 
                for m in ["a","b","c"]]
        self.state.phase_progress[3]=50
        
        r, error = self.run_oc(f"""Original task: {self.user_prompt[:150]}

Manager A Summary:
{self.state.managers['a'].summary[:200] if self.state.managers['a'].status=='complete' else 'FAILED'}

Manager B Summary:
{self.state.managers['b'].summary[:200] if self.state.managers['b'].status=='complete' else 'FAILED'}

Manager C Summary:
{self.state.managers['c'].summary[:200] if self.state.managers['c'].status=='complete' else 'FAILED'}

Evaluate and provide JSON response.""", 
                       self.repo_path, t=480, agent="judge")
        
        if r:
            try:
                rp = r.get("response","{}"); s,e = rp.find("{"), rp.rfind("}")+1
                d = json.loads(rp[s:e] if s>=0 and e>s else rp)
                
                for m, sc in d.get("scores",{}).items():
                    if m in self.state.managers: self.state.managers[m].score = sc
                
                w = d.get("winner","a"); self.state.winner = w
                scores_text = ",".join([f"{k.upper()}={v}" for k,v in d['scores'].items()])
                
                self.log(f"Scores R{round_num}: {scores_text}", lvl="JUDGE")
                self.log(f"Winner: {w.upper()}", lvl="WINNER")
                
                return d.get("scores", {})
            except Exception as parse_error:
                # Fallback - failed to parse judge response
                self.log(f"Judge parse error: {parse_error}", lvl="ERROR")
                for m in ["a","b","c"]:
                    if self.state.managers[m].status=="complete":
                        self.state.winner=m; self.state.managers[m].score=85
                        self.log(f"Fallback winner R{round_num}: {m.upper()}", lvl="WINNER")
                        return {"a": 85, "b": 0, "c": 0}
                return {}
        else:
            # Judge failed to run
            if error:
                self.log(f"Judge failed: {error[:200]}", lvl="ERROR")
            # Fallback - pick first complete manager
            for m in ["a","b","c"]:
                if self.state.managers[m].status=="complete":
                    self.state.winner=m; self.state.managers[m].score=85
                    self.log(f"Fallback winner R{round_num}: {m.upper()}", lvl="WINNER")
                    return {m: 85}
        
        self.state.phase_progress[3]=100
        return {}
    
    def check_quality(self, scores: dict) -> bool:
        """Check if all scores are below threshold"""
        if not scores:
            return False
        
        all_scores = [s for s in scores.values() if s is not None and s > 0]
        if not all_scores:
            return False
        
        max_score = max(all_scores)
        avg_score = sum(all_scores) / len(all_scores)
        
        # All below threshold?
        if max_score < self.QUALITY_THRESHOLD:
            self.log(f"Low quality detected: max={max_score}, avg={avg_score:.1f}", lvl="WARNING")
            return True
        
        return False
    
    def p5_cleanup(self):
        self.log("Cleanup"); self.state.current_phase=4
        for m in ["a","b","c"]:
            if m != self.state.winner:
                mg = self.state.managers[m]
                if mg.worktree and mg.worktree.exists():
                    subprocess.run(["git","worktree","remove",str(mg.worktree),"--force"], 
                                 cwd=self.repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(["git","branch","-D",mg.branch], 
                                 cwd=self.repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.log(f"Rm {m.upper()}", lvl="SUCCESS")
        self.state.phase_progress[4]=100
    
    def p6_pr(self):
        self.log("PR desc"); self.state.current_phase=5
        w = self.state.managers[self.state.winner]
        r, error = self.run_oc(f"""Original task: {self.user_prompt}

Winning implementation: Manager {self.state.winner.upper()}
Score: {w.score}/100
Round: {w.round}

Summary: {w.summary}

Generate PR description.""", 
                       self.repo_path, t=300, agent="pr-creator")
        if r:
            (w.worktree / "PR_DESCRIPTION.md").write_text(r.get("response",""))
            self.log("PR done", lvl="SUCCESS")
        elif error:
            self.log(f"PR generation failed: {error[:200]}", lvl="ERROR")
        self.state.phase_progress[5]=100
    
    def run(self):
        layout = self.make_layout()
        
        # Flag to stop render thread
        self.running = True
        
        def render_loop():
            """Background thread to update TUI"""
            while self.running:
                try:
                    self.render(layout)
                    time.sleep(0.25)  # 4 Hz refresh rate
                except:
                    pass
        
        # Start render thread
        render_thread = threading.Thread(target=render_loop, daemon=True)
        render_thread.start()
        
        with Live(layout, refresh_per_second=4, screen=True, console=self.console):
            try:
                self.log("MiniDani Starting...")
                
                # Round 1
                self.state.current_round = 1
                self.p1_branch(); time.sleep(1)
                self.p2_setup(round_num=1); time.sleep(1)
                self.p3_managers(round_num=1); time.sleep(1)
                scores_r1 = self.p4_judge(round_num=1); time.sleep(2)
                
                # Check if retry needed
                if self.check_quality(scores_r1):
                    self.log("⚠️  All scores < 80. Starting Round 2...", lvl="WARNING")
                    time.sleep(3)
                    
                    # Reset phases for round 2
                    self.state.phase_progress = {i: 0.0 for i in range(6)}
                    self.state.phase_progress[0] = 100  # Branch already done
                    self.state.current_round = 2
                    self.state.winner = None
                    
                    # Round 2
                    self.p2_setup(round_num=2); time.sleep(1)
                    self.p3_managers(round_num=2); time.sleep(1)
                    scores_r2 = self.p4_judge(round_num=2); time.sleep(2)
                    
                    # If still low, keep best from both rounds
                    if self.check_quality(scores_r2):
                        self.log("⚠️  Round 2 also low. Using best available.", lvl="WARNING")
                        time.sleep(2)
                
                # Cleanup and PR
                self.p5_cleanup(); time.sleep(1)
                self.p6_pr(); time.sleep(3)
                
                el = (datetime.now() - self.state.start_time).total_seconds()
                self.log(f"Done {el:.1f}s", lvl="SUCCESS")
                
                # Stop render thread
                self.running = False
                
                # Print debug logs if enabled
                self.print_debug_logs()
                
                return {
                    "success": True,
                    "winner": self.state.winner,
                    "branch": self.state.managers[self.state.winner].branch,
                    "round": self.state.managers[self.state.winner].round,
                    "scores": {m: self.state.managers[m].score for m in ["a","b","c"]},
                    "elapsed": el
                }
            except Exception as e:
                self.log(f"Fatal:{e}", lvl="ERROR"); time.sleep(3)
                # Stop render thread
                self.running = False
                
                # Print debug logs even on error
                self.print_debug_logs()
                
                return {"success": False, "error": str(e)}
            finally:
                # Ensure render thread stops
                self.running = False

if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(
        description="MiniDani - Competitive AI workflow orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  minidani "Create a REST API"                      # Inline prompt
  minidani -f prompt.md                              # From file
  cat prompt.md | minidani                           # From stdin
  minidani < prompt.md                               # From stdin redirect
  
  # Custom branch prefix
  minidani --branch-prefix "feat/" "Add auth"        # Use feat/ prefix
  export BRANCH_PREFIX="bugfix/"                     # Set default prefix
  minidani "Fix login bug"                           # Uses bugfix/ prefix
  
  # Debug mode
  minidani -d "Create API"                           # Show debug logs at end
  minidani --debug -f prompt.md                      # Debug with file input
        """
    )
    
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Task prompt (or omit to read from stdin/file)"
    )
    parser.add_argument(
        "-f", "--file",
        type=Path,
        help="Read prompt from file"
    )
    parser.add_argument(
        "--branch-prefix",
        type=str,
        default=None,
        help="Branch prefix (e.g., 'feature/', 'feat/', 'bugfix/'). Defaults to $BRANCH_PREFIX env var or no prefix"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug mode - print detailed logs after execution"
    )
    
    args = parser.parse_args()
    
    # Determine prompt source
    prompt = None
    
    if args.file:
        # Read from file
        if not args.file.exists():
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        prompt = args.file.read_text().strip()
    elif args.prompt:
        # Read from arguments
        prompt = " ".join(args.prompt)
    elif not sys.stdin.isatty():
        # Read from stdin (pipe or redirect)
        prompt = sys.stdin.read().strip()
    else:
        # No input provided
        parser.print_help()
        sys.exit(1)
    
    if not prompt:
        print("Error: Empty prompt")
        sys.exit(1)
    
    # Determine branch prefix (priority: CLI arg > env var > none)
    branch_prefix = args.branch_prefix
    if branch_prefix is None:
        branch_prefix = os.getenv("BRANCH_PREFIX", "")
    
    # Ensure prefix ends with / if not empty
    if branch_prefix and not branch_prefix.endswith("/"):
        branch_prefix += "/"
    
    # Use current working directory as the repository path
    repo_path = Path.cwd()
    
    minidani = MiniDaniRetry(repo_path, prompt, branch_prefix=branch_prefix, debug=args.debug)
    result = minidani.run()
    
    print("\n" + "="*70)
    print("RESULT:", json.dumps(result, indent=2))
