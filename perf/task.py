import random
import subprocess
import re
import time
import sys
import argparse


class Task:
    def __init__(self, test_name: str, cmd: str, threads: int, xs_path: str) -> None:
        self.test_name = test_name
        self.threads = threads
        self.xs_path = xs_path
        self.cmd = cmd
        self.pid: int
        self.stdout_file: str
        self.stderr_file: str
    
    def start(self, moniter_file: str, stdout_file: str, stderr_file: str) -> int:
        self.stdout_file = stdout_file
        exit_code = f'echo exit_code:$?E'
        command = f"NOOP_HOME={self.xs_path} && ({self.cmd} > {stdout_file} 2> {stderr_file}; {exit_code} > {moniter_file})"
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, stderr=subprocess.PIPE, text=True)
        return proc.pid
    

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task runner")

    # Parameters for __init__ method
    parser.add_argument("--test_name", type=str, required=True, help="Name of the test")
    parser.add_argument("--cmd", type=str, required=True, help="Command to run")
    parser.add_argument("--threads", type=int, required=True, help="Number of threads")
    parser.add_argument("--xs_path", type=str, required=True, help="Path to NOOP_HOME")

    # Parameters for start method
    parser.add_argument("--moniter_file", type=str, required=True, help="Monitor file")
    parser.add_argument("--stdout_file", type=str, required=True, help="Standard output file")
    parser.add_argument("--stderr_file", type=str, required=True, help="Standard error file")

    args = parser.parse_args()

    # Create Task instance
    task = Task(args.test_name, args.cmd, args.threads, args.xs_path)
    
    # Start the task and print the PID
    pid = task.start(args.moniter_file, args.stdout_file, args.stderr_file)
    print(pid)