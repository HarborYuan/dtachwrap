import sys
import subprocess
import threading
import argparse
import os
import select

def tee_stream(src_fd, dest_file_path, std_fd):
    """Reads from src_fd, writes to dest_file_path and std_fd."""
    try:
        with open(dest_file_path, "ab") as f:
            while True:
                data = os.read(src_fd, 4096)
                if not data:
                    break
                # Write to log
                f.write(data)
                f.flush()
                # Write to stdout/stderr
                # We use os.write to avoid python buffering issues on std_fd if possible, 
                # but std_fd passed here is sys.stdout/err file object usually.
                # simpler: os.write(std_fd.fileno(), data)
                try:
                    os.write(std_fd.fileno(), data)
                except OSError:
                    pass # maybe closed
    except Exception as e:
        pass # Ignore errors to avoid crashing wrapper

def tee_joint_stream(stdout_fd, stderr_fd, joint_file_path, stdout_file_path, stderr_file_path):
    """Reads from both stdout_fd and stderr_fd, writes to joint file and separate files."""
    try:
        with open(joint_file_path, "ab") as f_joint, \
             open(stdout_file_path, "ab") as f_out, \
             open(stderr_file_path, "ab") as f_err:
            
            fds = {stdout_fd: (f_out, sys.stdout), stderr_fd: (f_err, sys.stderr)}
            fd_list = list(fds.keys())
            
            while fd_list:
                ready, _, _ = select.select(fd_list, [], [])
                for fd in ready:
                    try:
                        data = os.read(fd, 4096)
                        if not data:
                            # EOF - remove from list
                            fd_list.remove(fd)
                            continue
                        
                        # Write to joint log file
                        f_joint.write(data)
                        f_joint.flush()
                        
                        # Write to individual log file
                        individual_file, std_fd = fds[fd]
                        individual_file.write(data)
                        individual_file.flush()
                        
                        # Write to stdout (all output goes to stdout in joint mode)
                        try:
                            os.write(sys.stdout.fileno(), data)
                        except OSError:
                            pass
                    except OSError:
                        # Error reading, remove fd
                        if fd in fd_list:
                            fd_list.remove(fd)
    except Exception as e:
        pass # Ignore errors to avoid crashing wrapper

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=False)
    parser.add_argument("--err", required=False)
    parser.add_argument("--joint", required=False)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    # command[0] might be '--'
    cmd = args.command
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
        
    if not cmd:
        return

    # Force PYTHONUNBUFFERED=1
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    # Start subprocess
    # stdin inherits
    p = subprocess.Popen(
        cmd,
        stdin=sys.stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0, # unbuffered
        env=env
    )

    if args.joint:
        # Joint stream mode - requires both --out and --err to be specified
        if not args.out or not args.err:
            sys.stderr.write("Error: --joint requires both --out and --err to be specified\n")
            sys.exit(1)
        t = threading.Thread(target=tee_joint_stream, args=(
            p.stdout.fileno(), p.stderr.fileno(), args.joint, args.out, args.err))
        threads = [t]
    else:
        # Separate streams mode
        if not args.out or not args.err:
            sys.stderr.write("Error: both --out and --err are required\n")
            sys.exit(1)
        t1 = threading.Thread(target=tee_stream, args=(p.stdout.fileno(), args.out, sys.stdout))
        t2 = threading.Thread(target=tee_stream, args=(p.stderr.fileno(), args.err, sys.stderr))
        threads = [t1, t2]
    
    import signal
    def forward_signal(sig, frame):
         # Forward signal to child
         if p.poll() is None:
             p.send_signal(sig)

    signal.signal(signal.SIGTERM, forward_signal)
    signal.signal(signal.SIGINT, forward_signal)
    
    for t in threads:
        t.start()
    
    # Wait for process
    p.wait()
    
    for t in threads:
        t.join()
    
    sys.exit(p.returncode)

if __name__ == "__main__":
    main()
