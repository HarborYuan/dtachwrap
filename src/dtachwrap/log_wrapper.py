import sys
import subprocess
import threading
import argparse
import os

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--err", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    # command[0] might be '--'
    cmd = args.command
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
        
    if not cmd:
        return

    # Buffer size 0? unbuffered text?
    # We work with bytes.
    
    # Start subprocess
    # stdin inherits
    p = subprocess.Popen(
        cmd,
        stdin=sys.stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0 # unbuffered
    )

    t1 = threading.Thread(target=tee_stream, args=(p.stdout.fileno(), args.out, sys.stdout))
    t2 = threading.Thread(target=tee_stream, args=(p.stderr.fileno(), args.err, sys.stderr))
    
    import signal
    def forward_signal(sig, frame):
         # Forward signal to child
         if p.poll() is None:
             p.send_signal(sig)

    signal.signal(signal.SIGTERM, forward_signal)
    signal.signal(signal.SIGINT, forward_signal)
    
    t1.start()
    t2.start()
    
    # Wait for process
    p.wait()
    
    t1.join()
    t2.join()
    
    sys.exit(p.returncode)

if __name__ == "__main__":
    main()
