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
    def __init__(self, repo_path: Path, user_prompt: str):
        self.repo_path, self.user_prompt = repo_path, user_prompt
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
    
    def run_oc(self, p, c=None, t=300, agent=None):
        """Run OpenCode with optional agent system prompt"""
        try:
            # If agent is specified, prepend agent instructions to prompt
            if agent:
                agent_path = Path(__file__).parent / ".opencode" / "agents" / f"{agent}.md"
                if agent_path.exists():
                    agent_prompt = agent_path.read_text()
                    p = f"{agent_prompt}\n\n---\n\n{p}"
            
            r = subprocess.run([str(self.opencode), "-p", p, "-f", "json"] + (["-c", str(c)] if c else []), 
                             capture_output=True, text=True, timeout=t)
            return json.loads(r.stdout) if r.returncode==0 else None
        except: return None
    
    def p1_branch(self):
        if self.state.branch_base:  # Already have branch from round 1
            return
        self.log("Gen branch"); self.state.current_phase=0
        r = self.run_oc(f"Task description:\n{self.user_prompt}", self.repo_path, agent="branch-namer")
        bn = "feature/task"
        if r:
            for l in r.get("response","").split("\n"):
                if l.strip().startswith("feature/") and len(l)<50: bn=l.strip(); break
        self.state.branch_base = bn; self.state.phase_progress[0]=100
        self.log(f"Branch: {bn}", lvl="SUCCESS")
    
    def p2_setup(self, round_num: int):
        self.log(f"Setup worktrees (Round {round_num})"); self.state.current_phase=1
        
        # Cleanup previous round if any
        for i, m in enumerate(["a","b","c"]):
            mg = self.state.managers[m]
            if mg.worktree and mg.worktree.exists():
                subprocess.run(["git","worktree","remove",str(mg.worktree),"--force"], 
                             cwd=self.repo_path, stderr=subprocess.DEVNULL)
                if mg.branch:
                    subprocess.run(["git","branch","-D",mg.branch], 
                                 cwd=self.repo_path, stderr=subprocess.DEVNULL)
            
            # Create new worktree
            br = f"{self.state.branch_base}-r{round_num}-{m}"
            wt = self.repo_path.parent / f"{self.repo_path.name}_worktree_r{round_num}_{m}"
            
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
            r = self.run_oc(f"User task:\n{self.user_prompt}{feedback}", 
                          m.worktree, t=1800, agent="manager")
            if r:
                m.summary, m.status, m.last_activity = r.get("response","")[:500], "complete", "Done"
                subprocess.run(["git","add","."], cwd=m.worktree)
                subprocess.run(["git","commit","-m",f"feat: r{round_num} {mid}"], 
                             cwd=m.worktree, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.log(f"OK R{round_num}", mgr=f"M{mid.upper()}", lvl="SUCCESS")
            else:
                m.status, m.last_activity = "failed", "Failed"
                self.log(f"Fail R{round_num}", mgr=f"M{mid.upper()}")
        except Exception as e:
            m.status, m.last_activity = "failed", str(e)[:30]
            self.log(f"Err R{round_num}:{e}", mgr=f"M{mid.upper()}")
    
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
        
        r = self.run_oc(f"""Original task: {self.user_prompt[:150]}

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
            except:
                # Fallback
                for m in ["a","b","c"]:
                    if self.state.managers[m].status=="complete":
                        self.state.winner=m; self.state.managers[m].score=85
                        self.log(f"Fallback winner R{round_num}: {m.upper()}", lvl="WINNER")
                        return {"a": 85, "b": 0, "c": 0}
                return {}
        
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
        r = self.run_oc(f"""Original task: {self.user_prompt}

Winning implementation: Manager {self.state.winner.upper()}
Score: {w.score}/100
Round: {w.round}

Summary: {w.summary}

Generate PR description.""", 
                       self.repo_path, t=300, agent="pr-creator")
        if r:
            (w.worktree / "PR_DESCRIPTION.md").write_text(r.get("response",""))
            self.log("PR done", lvl="SUCCESS")
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
                return {"success": False, "error": str(e)}
            finally:
                # Ensure render thread stops
                self.running = False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MiniDani - Competitive AI workflow orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  minidani "Create a REST API"              # Inline prompt
  minidani -f prompt.md                      # From file
  cat prompt.md | minidani                   # From stdin
  minidani < prompt.md                       # From stdin redirect
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
    
    # Use current working directory as the repository path
    repo_path = Path.cwd()
    
    minidani = MiniDaniRetry(repo_path, prompt)
    result = minidani.run()
    
    print("\n" + "="*70)
    print("RESULT:", json.dumps(result, indent=2))
