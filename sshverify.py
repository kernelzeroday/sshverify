import paramiko
import sys
import concurrent.futures
import threading
import time

MAX_THREADS = 50

class TimeoutThread:
    def __init__(self, func, args=(), timeout=5):
        self.func = func
        self.args = args
        self.timeout = timeout
        self.result = None
        self.finished = False

    def worker(self):
        self.result = self.func(*self.args)
        self.finished = True

    def execute(self):
        thread = threading.Thread(target=self.worker)
        thread.start()
        thread.join(self.timeout)
        if not self.finished:
            return f"Error: Execution timed out after {self.timeout} seconds"
        return self.result

def ssh_and_get_version(ip, port, user, password):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, port=port, username=user, password=password, timeout=3)

        with client.invoke_shell() as ssh:
            ssh.send('cat /proc/version\n')
            time.sleep(1)  # Give the command some time to execute
            result = ssh.recv(4096).decode('utf-8').strip()
        
        client.close()
        
        # Removing newlines, carriage returns, and trimming whitespace
        return result.replace("\n", "").replace("\r", "").strip()
        
    except Exception as e:
        return f"Error: {str(e)}"

def process_line(line):
    ip, port, user, password = line.strip().split(":")
    tt = TimeoutThread(ssh_and_get_version, args=(ip, int(port), user, password), timeout=3)
    result = tt.execute()
    return f"{ip}:{port}:{user}:{password}:{result}"

def main():
    # Check if output filename is provided
    if len(sys.argv) < 2:
        print("Usage: python script_name.py output_filename")
        sys.exit(1)

    output_file = sys.argv[1]

    with open(output_file, "w") as outfile:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            results = list(executor.map(process_line, sys.stdin))
            for result in results:
                outfile.write(result + "\n")
                print(f"Processed: {result.split(':')[0]}:{result.split(':')[1]}")

if __name__ == "__main__":
    main()

