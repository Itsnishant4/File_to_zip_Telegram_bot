import socket
import subprocess
import os
import sys

def bind_port(port):
    """
    Bind to a given port to ensure it's available.
    """
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("0.0.0.0", port))
        server_socket.listen(1)
        print(f"Port {port} is bound and ready.")
        return server_socket
    except OSError as e:
        print(f"Failed to bind port {port}: {e}")
        exit(1)

def run_script(script_name):
    """
    Run another Python script using subprocess.
    """
    try:
        print(f"Starting script {script_name}...")
        subprocess.run([sys.executable, script_name])
    except FileNotFoundError as e:
        print(f"Error: {e}. Ensure the script path is correct.")
    except Exception as e:
        print(f"An error occurred while running {script_name}: {e}")

if __name__ == "__main__":
    PORT = 8443
    # Bind to the port
    server_socket = bind_port(PORT)

    # Run the secondary script (fz.py)
    script_path = "/Users/nishant/Downloads/fz.py"  # Full path to your script
    run_script(script_path)

    # Cleanup when done
    server_socket.close()
    print(f"Port {PORT} is now released.")
