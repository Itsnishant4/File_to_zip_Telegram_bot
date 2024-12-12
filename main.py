import http.server
import socketserver
import subprocess
import os
import sys
from threading import Thread

def bind_and_serve(port):
    """
    Bind to a port and serve basic HTTP traffic.
    """
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Port is ready and HTTP traffic is being served.")

    try:
        with socketserver.TCPServer(("0.0.0.0", port), Handler) as httpd:
            print(f"Serving HTTP on port {port}")
            httpd.serve_forever()
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
        print(f"Script {script_name} exited with error: {e}")
    except Exception as e:
        print(f"An error occurred while running {script_name}: {e}")

if __name__ == "__main__":
    PORT = 8443

    # Start HTTP server in a separate thread
    server_thread = Thread(target=bind_and_serve, args=(PORT,), daemon=True)
    server_thread.start()

    # Run the secondary script (fz.py)
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fz.py")
    run_script(script_path)

    # Join server thread to keep the script alive if needed
    server_thread.join()