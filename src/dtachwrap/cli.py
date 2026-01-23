import os
import sys
import time
import signal
import typer
import subprocess
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from dtachwrap import dtachbin, state, proc
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="dtachwrap: Python wrapper for dtach")

@app.command(context_settings={"ignore_unknown_options": True})
def start(
    name: str = typer.Argument(..., help="Task name"),
    command: List[str] = typer.Argument(..., help="Command to run"),
    workdir: Optional[Path] = typer.Option(None, help="Working directory"),
    root: Optional[Path] = typer.Option(None, help="Root storage directory"),
):
    """
    Start a new task under dtach.
    """
    root_path = state.get_root(root)
    state.ensure_dirs(root_path)
    
    clean_name = state.sanitize_name(name)
    
    # Check if exists
    existing = state.TaskMeta.load(clean_name, root_path)
    if existing and proc.is_alive(existing.dtach_pid):
        typer.echo(f"Task '{clean_name}' is already running (pid {existing.dtach_pid}).", err=True)
        raise typer.Exit(1)
    
    # Paths
    socket_path = root_path / "sockets" / clean_name
    meta_path = root_path / "meta" / f"{clean_name}.json"
    log_out = root_path / "logs" / f"{clean_name}.out"
    log_err = root_path / "logs" / f"{clean_name}.err"
    
    # Socket path length check
    if len(str(socket_path)) > 100:
        typer.echo(f"Warning: Socket path length {len(str(socket_path))} might be too long.", err=True)
    
    cwd = workdir if workdir else Path.cwd()
    
    # Get dtach binary
    try:
        dtach_exe = dtachbin.get_dtach_path()
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
        
    # Open logs
    f_out = open(log_out, "a")
    f_err = open(log_err, "a")
    
    # Use internal python wrapper to capture logs
    # This works cross-platform (where python is available) and handle separate streams
    wrapper_cmd = [sys.executable, "-u", "-m", "dtachwrap.log_wrapper", "--out", str(log_out), "--err", str(log_err), "--"] + command
    
    cmd_args = [dtach_exe, "-N", str(socket_path), "--"] + wrapper_cmd
    
    # Launch
    try:
        p = subprocess.Popen(
            cmd_args,
            cwd=str(cwd),
            stdout=f_out,
            stderr=f_err,
            stdin=subprocess.DEVNULL,
            start_new_session=True # setsid
        )
        
        # Check if started
        time.sleep(0.2)
        if p.poll() is not None:
            if p.returncode != 0:
                typer.echo(f"Failed to start dtach. Exit code: {p.returncode}", err=True)
                raise typer.Exit(1)
            # If 0, it finished quickly (short task), which is fine.
            
    except Exception as e:
        typer.echo(f"Error starting process: {e}", err=True)
        raise typer.Exit(1)

    # Save meta
    meta = state.TaskMeta(
        name=clean_name,
        dtach_pid=p.pid,
        cmd=" ".join(command),
        argv=command,
        workdir=str(cwd),
        socket_path=str(socket_path),
        stdout_path=str(log_out),
        stderr_path=str(log_err),
        started_at=datetime.now().isoformat()
    )
    
    child_pids = proc.get_children_pids(p.pid)
    if child_pids:
        meta.child_pid = child_pids[0]
        
    meta.save(root_path)
    
    typer.echo(f"Started task '{clean_name}'")
    typer.echo(f"  Socket: {socket_path}")
    typer.echo(f"  Logs: {log_out}")
    typer.echo(f"  PID: {p.pid} (dtach)" + (f", {meta.child_pid} (task)" if meta.child_pid else ""))


@app.command()
def attach(
    name: str,
    detach_key: str = typer.Option("^\\", help="Detach key (e.g. ^\\)"),
    redraw: str = typer.Option("ctrl_l", help="Redraw method: ctrl_l, winch, none"),
    no_suspend: bool = typer.Option(False, "--no-suspend", help="Disable suspend processing"),
    root: Optional[Path] = typer.Option(None),
):
    """
    Attach to a running task.
    """
    root_path = state.get_root(root)
    clean_name = state.sanitize_name(name)
    meta = state.TaskMeta.load(clean_name, root_path)
    
    if not meta:
        typer.echo(f"Task '{clean_name}' not found.", err=True)
        raise typer.Exit(1)
    
    if not Path(meta.socket_path).exists():
         typer.echo(f"Socket for '{clean_name}' not found at {meta.socket_path}.", err=True)
         raise typer.Exit(1)

    dtach_exe = dtachbin.get_dtach_path()
    
    cmd = [dtach_exe, "-a", meta.socket_path]
    if detach_key:
        cmd.extend(["-e", detach_key])
        
    if redraw != "none":
        cmd.extend(["-r", redraw])
        
    if no_suspend:
        cmd.append("-z")
        
    os.execv(dtach_exe, cmd)


@app.command()
def ls(
    all: bool = typer.Option(False, "--all", help="Show dead tasks"),
    root: Optional[Path] = typer.Option(None),
):
    """
    List tasks.
    """
    root_path = state.get_root(root)
    metas = state.TaskMeta.list_all(root_path)
    
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("PID")
    table.add_column("Started")
    table.add_column("Command")
    
    for m in metas:
        alive = proc.is_alive(m.dtach_pid)
        status = "RUNNING" if alive else "DEAD"
        
        if not all and not alive:
            continue
            
        style = "green" if alive else "red"
        
        table.add_row(
            m.name,
            f"[{style}]{status}[/{style}]",
            str(m.dtach_pid),
            m.started_at,
            m.cmd[:50],
        )
        
    console.print(table)


@app.command()
def logs(
    name: str,
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow log output"),
    err: bool = typer.Option(False, "--err", help="Show stderr instead of stdout"),
    root: Optional[Path] = typer.Option(None),
):
    """
    Show logs for a task.
    """
    root_path = state.get_root(root)
    clean_name = state.sanitize_name(name)
    meta = state.TaskMeta.load(clean_name, root_path)
    if not meta:
        typer.echo(f"Task '{clean_name}' not found.", err=True)
        raise typer.Exit(1)
        
    log_file = meta.stderr_path if err else meta.stdout_path
    if not Path(log_file).exists():
        typer.echo(f"Log file not found: {log_file}", err=True)
        raise typer.Exit(1)
        
    cmd = ["tail", "-n", "200"]
    if follow:
        cmd.append("-f")
    cmd.append(log_file)
    
    os.execvp("tail", cmd)

@app.command()
def stop(
    name: str,
    sig: str = typer.Option("TERM", help="Signal to send (TERM, INT, KILL)"),
    grace_seconds: int = 5,
    root: Optional[Path] = typer.Option(None),
):
    """
    Stop a task.
    """
    root_path = state.get_root(root)
    clean_name = state.sanitize_name(name)
    meta = state.TaskMeta.load(clean_name, root_path)
    if not meta:
        typer.echo(f"Task '{clean_name}' not found.", err=True)
        raise typer.Exit(1)
        
    # Resolve signal
    sig_map = {
        "TERM": signal.SIGTERM,
        "INT": signal.SIGINT,
        "KILL": signal.SIGKILL
    }
    s = sig_map.get(sig.upper(), signal.SIGTERM)
    
    # 1. Kill child if known
    if meta.child_pid and proc.is_alive(meta.child_pid):
        typer.echo(f"Sending {sig} to child {meta.child_pid}...")
        proc.kill_process(meta.child_pid, s)
        
        start_t = time.time()
        while proc.is_alive(meta.child_pid) and (time.time() - start_t < grace_seconds):
            time.sleep(0.1)
            
        if proc.is_alive(meta.child_pid):
            typer.echo("Child still alive, forcing KILL...")
            proc.kill_process(meta.child_pid, signal.SIGKILL)
            
    # 2. Kill dtach
    if proc.is_alive(meta.dtach_pid):
        typer.echo(f"Stopping dtach {meta.dtach_pid}...")
        proc.kill_process(meta.dtach_pid, signal.SIGTERM)
        
        start_t = time.time()
        while proc.is_alive(meta.dtach_pid) and (time.time() - start_t < grace_seconds):
            time.sleep(0.1)
            
        if proc.is_alive(meta.dtach_pid):
            proc.kill_process(meta.dtach_pid, signal.SIGKILL)
            
    typer.echo(f"Stopped {clean_name}")

if __name__ == "__main__":
    app()
