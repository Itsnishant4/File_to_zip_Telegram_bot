import socket
import subprocess
import os
import sys
import argparse

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
        subprocess.run([sys.executable, script_name], check=True)
    except FileNotFoundError as e:
        print(f"Error: {e}. Ensure the script path is correct.")
    except subprocess.CalledProcessError as e:
        print(f"Script {script_name} exited with an error: {e}")
    except Exception as e:
        print(f"An error occurred while running {script_name}: {e}")

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Bind a port and run a script.")
    parser.add_argument("--port", type=int, default=8443, help="Port to bind to")
    parser.add_argument("--script", type=str, default="fz.py", help="Script to run")
    args = parser.parse_args()

    # Bind to the specified port
    PORT = args.port
    server_socket = bind_port(PORT)

    # Get the full path of the script to run
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.script)

    # Check if the script exists
    if not os.path.isfile(script_path):
        print(f"Error: The script {args.script} was not found at {script_path}.")
        server_socket.close()
        exit(1)

    # Run the secondary script
    run_script(script_path)

    # Cleanup
    server_socket.close()
    print(f"Port {PORT} is now released.")
