import signal
import sys
import time

# Flag to indicate shutdown requested
shutdown_requested = False

# Signal handler for SIGTERM and SIGINT
def handle_signal(signum, frame):
    global shutdown_requested
    print(f"\n[INFO] Signal {signum} received. Preparing to shut down.")
    time.sleep(20)
    shutdown_requested = True
    print("Beendet")

# Register signal handlers
signal.signal(signal.SIGINT, handle_signal)   # Ctrl+C (SIGINT)
signal.signal(signal.SIGTERM, handle_signal)  # Terminate (SIGTERM)

try:
    while not shutdown_requested:
        print("Running")
        time.sleep(1)
except Exception:
    print("Beendet")