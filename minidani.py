#!/usr/bin/env python3
"""
MiniDani with Retry Logic - If all scores < 80, launch second round
"""

import subprocess, json, time, threading, sys, tempfile, signal
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
    pr_url: Optional[str] = None

class MiniDaniRetry:
    def __init__(self, repo_path: Path, user_prompt: str, branch_prefix: str = "", branch_name: str = "", debug: bool = False):
        self.repo_path, self.user_prompt = repo_path, user_prompt
        self.branch_prefix = branch_prefix
        self.branch_name = branch_name  # Manual branch name (overrides generation)
        self.debug = debug
        self.debug_logs = []  # Accumulate debug logs here
        # Find opencode in PATH (installed via npm globally)
        import shutil
        self.opencode = shutil.which("opencode")
        self.console, self.lock = Console(), threading.Lock()
        if not self.opencode: raise FileNotFoundError("OpenCode not found in PATH. Install with: npm install -g opencode-ai")
        
        # Agent timeouts for OpenCode agents (models defined in agent .md frontmatter)
        # Note: branch-namer now uses generate_branch_name.py (not an OpenCode agent)
        self.agent_timeouts = {
            "manager": 1800,
            "judge": 480,
            "pr-creator": 300,
            "red-team": 1800,
            "blue-team": 1200,
            "_default": 300
        }
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
    
    # get_input_with_timeout() removed - branch name now specified via --branch-name or auto-generated
    
    def run_oc(self, p, c=None, t=None, agent=None, log_prefix="OpenCode"):
        """Run OpenCode with optional agent. Returns (result, error_msg)
        
        Args:
            p: Prompt text
            c: Working directory path
            t: Timeout (overrides default if provided)
            agent: Agent name (OpenCode built-in or custom agent)
            log_prefix: Prefix for log messages (e.g., "MA", "Judge")
        
        New CLI (v1.1.x): opencode run "message" --agent <name> --format json
        """
        try:
            # Get timeout for agent
            timeout = t if t is not None else self.agent_timeouts.get(agent, 300)
            
            # Log start
            self.log(f"Starting {agent or 'opencode'} (timeout: {timeout}s)", mgr=log_prefix, lvl="INFO")
            
            # Build command: opencode run "prompt" [--agent <name>] --format json
            cmd = [str(self.opencode), "run", p, "--format", "json"]
            
            # Add agent if specified
            if agent:
                cmd.extend(["--agent", agent])
            
            # Log command being executed
            self.log(f"Exec: opencode run '...' --agent {agent or 'default'} --format json", mgr=log_prefix, lvl="INFO")
            
            # Run command from working directory
            start_time = time.time()
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=c)
            elapsed = time.time() - start_time
            
            self.log(f"Completed in {elapsed:.1f}s", mgr=log_prefix, lvl="INFO")
            
            if r.returncode == 0:
                # OpenCode 1.1.x returns JSON events (newline-delimited)
                response_text = ""
                for line in r.stdout.strip().split('\n'):
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        # Handle different event types
                        if event.get("type") == "text":
                            # Text event with content
                            if "content" in event:
                                response_text += event["content"]
                            elif "part" in event and "text" in event["part"]:
                                response_text += event["part"]["text"]
                        elif event.get("type") == "message.complete":
                            # Final message event
                            if "content" in event:
                                response_text = event["content"]
                        elif "response" in event:
                            response_text += event["response"]
                    except json.JSONDecodeError:
                        # If not JSON, might be raw text
                        response_text += line
                
                return {"response": response_text}, None
            else:
                # Capture error information
                error_msg = f"Exit code {r.returncode}"
                if r.stderr:
                    error_msg += f"\nStderr: {r.stderr[:500]}"
                if r.stdout:
                    error_msg += f"\nStdout: {r.stdout[:500]}"
                return None, error_msg
        except subprocess.TimeoutExpired:
            return None, f"Timeout after {timeout}s"
        except Exception as e:
            return None, f"Exception: {str(e)}"
    
    def p1_branch(self):
        if self.state.branch_base:  # Already have branch from round 1
            return
        self.log("Determining branch name"); self.state.current_phase=0
        
        # Option 1: Manual branch name provided via --branch-name
        if self.branch_name:
            if not self._validate_branch_name(self.branch_name):
                raise ValueError(f"Invalid branch name: {self.branch_name} (no spaces or special chars allowed)")
            
            # Add prefix if configured
            bn = f"{self.branch_prefix}{self.branch_name}" if self.branch_prefix else self.branch_name
            self.log(f"Using manual branch name: {bn}", lvl="SUCCESS")
            self.state.branch_base = bn
            self.state.phase_progress[0] = 100
            return
        
        # Option 2: Generate with OpenAI (requires API key)
        self.log("Generating branch name with OpenAI...", lvl="INFO")
        
        try:
            script_path = Path(__file__).parent / "generate_branch_name.py"
            cmd = ["python3", str(script_path), self.user_prompt]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                descriptive_name = data.get("branch_name", None)
                
                if not descriptive_name:
                    raise ValueError("Branch name generator returned empty name")
                
                # Add prefix if configured
                bn = f"{self.branch_prefix}{descriptive_name}"
                self.log(f"Generated branch name: {bn}", lvl="SUCCESS")
                self.state.branch_base = bn
                self.state.phase_progress[0] = 100
            else:
                # Generation failed - check if it's missing API key
                stderr = result.stderr.lower()
                if "openai" in stderr or "api" in stderr or "key" in stderr or "modulenotfounderror" in stderr:
                    raise ValueError(
                        "OpenAI API not available. Please either:\n"
                        "  1. Install OpenAI: pip install openai\n"
                        "  2. Set OPENAI_API_KEY environment variable\n"
                        "  3. Or specify branch name manually: minidani --branch-name <name> ..."
                    )
                else:
                    raise ValueError(f"Branch name generation failed: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            raise ValueError("Branch name generation timed out. Use --branch-name to specify manually.")
        except json.JSONDecodeError:
            raise ValueError("Branch name generator returned invalid JSON. Use --branch-name to specify manually.")
        except Exception as e:
            if "openai" in str(e).lower() or "api" in str(e).lower():
                raise ValueError(
                    f"OpenAI API error: {str(e)[:100]}\n"
                    "Use --branch-name <name> to specify branch name manually."
                )
            raise
    
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
    
    def print_debug_report(self):
        """Print detailed report of what each component did"""
        if not self.debug:
            return
        
        print("\n" + "="*80)
        print("DETAILED DEBUG REPORT".center(80))
        print("="*80)
        
        # Manager summaries
        print("\n📊 MANAGER OUTPUTS:\n")
        for m_id in ["a", "b", "c"]:
            mgr = self.state.managers[m_id]
            print(f"--- Manager {m_id.upper()} ({mgr.status}) ---")
            if mgr.summary:
                print(f"Summary ({len(mgr.summary)} chars):")
                print(mgr.summary[:500])
                if len(mgr.summary) > 500:
                    print(f"... (truncated, {len(mgr.summary) - 500} more chars)")
            else:
                print("No summary (failed or not run)")
            print()
        
        # Judge output
        print("\n⚖️  JUDGE EVALUATION:\n")
        if hasattr(self, '_judge_raw_response'):
            print(f"Raw response ({len(self._judge_raw_response)} chars):")
            print(self._judge_raw_response[:1000])
            if len(self._judge_raw_response) > 1000:
                print(f"... (truncated, {len(self._judge_raw_response) - 1000} more chars)")
        else:
            print("No judge response captured")
        print()
        
        # Winner and PR
        if self.state.winner:
            print(f"\n🏆 WINNER: Manager {self.state.winner.upper()}")
            winner_mgr = self.state.managers[self.state.winner]
            if winner_mgr.worktree:
                pr_file = winner_mgr.worktree / "PR_DESCRIPTION.md"
                if pr_file.exists():
                    print(f"\n📝 PR DESCRIPTION ({pr_file}):")
                    print("-" * 80)
                    print(pr_file.read_text()[:1000])
                    print("-" * 80)
                else:
                    print("\n⚠️  No PR_DESCRIPTION.md found")
        
        print("\n" + "="*80 + "\n")
    
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
            
            # Delete branch if it already exists (prevents worktree creation failure)
            subprocess.run(["git","branch","-D",br], 
                         cwd=self.repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Create worktree - check for errors
            result = subprocess.run(["git","worktree","add",str(wt),"-b",br], 
                         cwd=self.repo_path, capture_output=True, text=True)
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "unknown error"
                self.log(f"WT {m.upper()} R{round_num} FAILED: {error_msg[:100]}", lvl="ERROR")
                # Try to clean up any partial worktree
                if wt.exists():
                    subprocess.run(["git","worktree","remove",str(wt),"--force"], 
                                 cwd=self.repo_path, stderr=subprocess.DEVNULL)
                raise Exception(f"Failed to create worktree for manager {m}: {error_msg[:200]}")
            
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
            # Timeout configured in agents.json (30 min for manager)
            r, error = self.run_oc(
                f"User task:\n{self.user_prompt}{feedback}", 
                m.worktree, 
                agent="manager",
                log_prefix=f"M{mid.upper()}"
            )
            if r:
                m.summary, m.status, m.last_activity = r.get("response","")[:500], "complete", "Done"
                # Don't commit here - let pr-creator decide what files to include in PR
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
        last_log_time = st
        
        while any(t.is_alive() for t in ts):
            time.sleep(2)
            elapsed = time.time() - st
            self.state.phase_progress[2]=(sum(1 for m in self.state.managers.values() if m.status=="complete")/3)*100
            
            # Log progress every 60 seconds
            if time.time() - last_log_time >= 60:
                completed = sum(1 for m in self.state.managers.values() if m.status=="complete")
                running = sum(1 for m in self.state.managers.values() if m.status=="running")
                self.log(f"Progress: {completed}/3 done, {running} running ({elapsed:.0f}s elapsed)", lvl="INFO")
                last_log_time = time.time()
            
            # Timeout after 900s (15 min)
            if elapsed > 900:
                self.log("Manager timeout reached (15 min), proceeding...", lvl="WARNING")
                break
        
        for t in ts: t.join(1)
        self.state.phase_progress[2]=100
        
        # Log final status of each manager
        for m in ["a", "b", "c"]:
            mg = self.state.managers[m]
            status_emoji = "✅" if mg.status == "complete" else "⏳" if mg.status == "running" else "❌"
            self.log(f"M{m.upper()}: {status_emoji} {mg.status}", lvl="INFO")
        
        self.log(f"All done R{round_num}", lvl="SUCCESS")
    
    def p4_judge(self, round_num):
        self.log(f"Judging R{round_num}", lvl="JUDGE"); self.state.current_phase=3
        sums = [f"M{m.upper()}: {self.state.managers[m].summary[:150] if self.state.managers[m].status=='complete' else 'FAIL'}" 
                for m in ["a","b","c"]]
        self.state.phase_progress[3]=50
        
        self.log("Preparing judge evaluation...", lvl="JUDGE")
        
        r, error = self.run_oc(
            f"""Original task: {self.user_prompt[:150]}

Manager A Summary:
{self.state.managers['a'].summary[:200] if self.state.managers['a'].status=='complete' else 'FAILED'}

Manager B Summary:
{self.state.managers['b'].summary[:200] if self.state.managers['b'].status=='complete' else 'FAILED'}

Manager C Summary:
{self.state.managers['c'].summary[:200] if self.state.managers['c'].status=='complete' else 'FAILED'}

Evaluate and provide JSON response.""",
            self.repo_path,
            agent="judge",
            log_prefix="Judge"
        )
        
        if r:
            try:
                rp = r.get("response","{}"); s,e = rp.find("{"), rp.rfind("}")+1
                # Capture for debug report
                self._judge_raw_response = rp
                d = json.loads(rp[s:e] if s>=0 and e>s else rp)
                
                for m, sc in d.get("scores",{}).items():
                    if m in self.state.managers: self.state.managers[m].score = sc
                
                w = d.get("winner","a").lower(); self.state.winner = w
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
    
    def cleanup_all_worktrees(self):
        """
        Clean up ALL worktrees and branches created by this session.
        Se ejecuta al finalizar (éxito, error o Ctrl+C) para prevenir corrupción.
        
        Maneja casos edge:
        - Worktrees que no existen físicamente pero están registrados en .git
        - Branches que ya no existen
        - Referencias corruptas
        """
        self.log("Cleaning up all worktrees...", lvl="INFO")
        
        cleaned_worktrees = 0
        cleaned_branches = 0
        
        for m in ["a", "b", "c"]:
            mg = self.state.managers[m]
            
            # Clean up worktree if it was created
            if mg.worktree:
                try:
                    # Intentar eliminar worktree (--force maneja casos corruptos)
                    result = subprocess.run(
                        ["git", "worktree", "remove", str(mg.worktree), "--force"],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        cleaned_worktrees += 1
                        self.log(f"Cleaned worktree {m.upper()}", lvl="SUCCESS")
                    else:
                        # Worktree ya no existe o error menor - no crítico
                        if "not found" not in result.stderr.lower():
                            self.log(f"Worktree {m.upper()} cleanup note: {result.stderr[:100]}", lvl="WARNING")
                except Exception as e:
                    self.log(f"Worktree {m.upper()} cleanup error: {str(e)[:100]}", lvl="WARNING")
            
            # Clean up branch if it was created
            if mg.branch:
                try:
                    result = subprocess.run(
                        ["git", "branch", "-D", mg.branch],
                        cwd=self.repo_path,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        cleaned_branches += 1
                        self.log(f"Cleaned branch {m.upper()}", lvl="SUCCESS")
                    else:
                        # Branch ya no existe - no crítico
                        if "not found" not in result.stderr.lower():
                            self.log(f"Branch {m.upper()} cleanup note: {result.stderr[:100]}", lvl="WARNING")
                except Exception as e:
                    self.log(f"Branch {m.upper()} cleanup error: {str(e)[:100]}", lvl="WARNING")
        
        # Clean up orphaned worktree references
        try:
            subprocess.run(
                ["git", "worktree", "prune"],
                cwd=self.repo_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.log("Pruned orphaned worktree refs", lvl="SUCCESS")
        except Exception as e:
            self.log(f"Prune error: {str(e)[:100]}", lvl="WARNING")
        
        self.log(f"Cleanup done: {cleaned_worktrees} worktrees, {cleaned_branches} branches", lvl="INFO")
    
    def p6_pr(self):
        self.log("Pushing and creating PR..."); self.state.current_phase=5
        w = self.state.managers[self.state.winner]
        
        self.log(f"Winner: {self.state.winner.upper()}, Score: {w.score}, Round: {w.round}", lvl="INFO")
        
        # Run pr-creator agent in the winner's worktree to stage, commit, push and create PR
        r, error = self.run_oc(
            f"""Original task: {self.user_prompt}

Winning implementation: Manager {self.state.winner.upper()}
Score: {w.score}/100

Summary of implementation: {w.summary}

Your job:
1. Check what files were created/modified (git status)
2. Stage ONLY production-relevant files (source code, tests, docs) - exclude .opencode/, plan.md, logs, __pycache__, etc.
3. Commit with a clear message describing the implementation
4. Push the branch to origin
5. Create a Pull Request using `gh pr create`

The PR title should briefly describe what was implemented.
Output the PR URL at the end.""",
            w.worktree,  # Run in winner's worktree
            agent="pr-creator",
            log_prefix="PR"
        )
        
        if r:
            response = r.get("response", "")
            # Try to extract PR URL from response
            import re
            pr_match = re.search(r'https://github\.com/[^\s]+/pull/\d+', response)
            if pr_match:
                self.state.pr_url = pr_match.group(0)
                self.log(f"PR created: {self.state.pr_url}", lvl="SUCCESS")
            else:
                self.log(f"PR response: {response[:300]}", lvl="INFO")
        elif error:
            self.log(f"PR creation failed: {error[:200]}", lvl="ERROR")
        
        self.state.phase_progress[5]=100
    
    def run(self):
        layout = self.make_layout()
        
        # Flag to stop render thread
        self.running = True
        
        # Register signal handler for Ctrl+C (cleanup before exit)
        def signal_handler(sig, frame):
            self.log("Ctrl+C detected, cleaning up...", lvl="WARNING")
            self.running = False
            self.cleanup_all_worktrees()
            sys.exit(1)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        def render_loop():
            """Background thread to update TUI"""
            while self.running:
                try:
                    self.render(layout)
                    time.sleep(0.25)  # 4 Hz refresh rate
                except:
                    pass
        
        # Start render thread
        # Get branch name approval BEFORE starting TUI (needs user input)
        try:
            self.log("MiniDani Starting...")
            
            # Clean up any orphaned worktrees from previous failed runs
            subprocess.run(["git","worktree","prune"], cwd=self.repo_path, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.state.current_round = 1
            self.p1_branch()
        except KeyboardInterrupt:
            self.cleanup_all_worktrees()
            return {"success": False, "error": "User cancelled during branch selection"}
        except ValueError as e:
            # Branch name generation/validation error
            return {"success": False, "error": str(e)}
        
        print("\n🚀 Starting parallel execution...\n")
        
        # Now start TUI for the rest
        render_thread = threading.Thread(target=render_loop, daemon=True)
        render_thread.start()
        
        with Live(layout, refresh_per_second=4, screen=True, console=self.console):
            try:
                # Round 1 (branch already set)
                time.sleep(0.5)
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
                self.print_debug_report()
                
                return {
                    "success": True,
                    "winner": self.state.winner,
                    "branch": self.state.managers[self.state.winner].branch,
                    "round": self.state.managers[self.state.winner].round,
                    "scores": {m: self.state.managers[m].score for m in ["a","b","c"]},
                    "elapsed": el,
                    "pr_url": self.state.pr_url
                }
            except Exception as e:
                self.log(f"Fatal:{e}", lvl="ERROR"); time.sleep(3)
                # Stop render thread
                self.running = False
                
                # Print debug logs even on error
                self.print_debug_logs()
                self.print_debug_report()
                
                return {"success": False, "error": str(e)}
            finally:
                # Ensure render thread stops
                self.running = False
                
                # Always cleanup worktrees (success, error, or interruption)
                # This prevents corrupted worktrees on next run
                self.cleanup_all_worktrees()

if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(
        description="MiniDani - Competitive AI workflow orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (auto-generates branch name with OpenAI)
  minidani "Create a REST API"                      # Inline prompt
  minidani -f prompt.md                              # From file
  cat prompt.md | minidani                           # From stdin
  minidani < prompt.md                               # From stdin redirect
  
  # Manual branch name (no OpenAI required)
  minidani -b add-auth "Add authentication"          # Specify branch name
  minidani --branch-name fix-login -f prompt.md      # From file with custom name
  
  # Custom branch prefix
  minidani --branch-prefix "feat/" "Add auth"        # Use feat/ prefix
  minidani -b login --branch-prefix "feat/" "..."    # Branch: feat/login
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
        "-b", "--branch-name",
        type=str,
        default=None,
        help="Branch name (required if OpenAI API not available). Will be prefixed with --branch-prefix if set."
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
    
    minidani = MiniDaniRetry(
        repo_path, 
        prompt, 
        branch_prefix=branch_prefix, 
        branch_name=args.branch_name or "",
        debug=args.debug
    )
    result = minidani.run()
    
    print("\n" + "="*70)
    print("RESULT:", json.dumps(result, indent=2))
