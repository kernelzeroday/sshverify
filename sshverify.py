import paramiko
import sys
import concurrent.futures
import threading
import time

MAX_THREADS = 75

class TimeoutThread:
    def __init__(self, func, args=(), timeout=8):
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
        client.connect(ip, port=port, username=user, password=password, timeout=8, banner_timeout=8)

        with client.invoke_shell() as ssh:
            ssh.send('cat /proc/version\n')
            time.sleep(2)  # Give the command some time to execute
            result = ssh.recv(4096).decode('utf-8').strip()
        
        client.close()
        
        # Removing newlines, carriage returns, and trimming whitespace
        return result.replace("\n", "").replace("\r", "").strip()
        
    except Exception as e:
        return f"Error: {str(e)}"

def process_line(line):
    ip, port, user, password = line.strip().split(":")
    tt = TimeoutThread(ssh_and_get_version, args=(ip, int(port), user, password), timeout=8)
    result = tt.execute()
    output = f"{ip}:{port}:{user}:{password}:{result}"
    print(f"Processed: {output.split(':')[0]}:{output.split(':')[1]}")
    return output

def main():
    # Check if output filename is provided
    if len(sys.argv) < 2:
        print("Usage: python script_name.py output_filename")
        sys.exit(1)

    output_file = sys.argv[1]

    with open(output_file, "w") as outfile:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            for result in executor.map(process_line, sys.stdin):
                outfile.write(result + "\n")

if __name__ == "__main__":
    main()

