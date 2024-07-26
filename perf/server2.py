import getpass
from fabric import Connection
import shlex
import time
import os
import subprocess
from typing import List, Optional, Tuple


def generate_command_args_shell(test_name, cmd, threads, xs_path, moniter_file, stdout_file, stderr_file):
    args = [
        "--test_name", shlex.quote(test_name),
        "--cmd", shlex.quote(cmd),
        "--threads", str(threads),
        "--xs_path", shlex.quote(xs_path),
        "--moniter_file", shlex.quote(moniter_file),
        "--stdout_file", shlex.quote(stdout_file),
        "--stderr_file", shlex.quote(stderr_file)
    ]
    return " ".join(args)


def generate_custom_path(stdout_file: str, custom_filename: str) -> str:
    """Generate a new file path in the same parent directory as stdout_file with a custom filename."""
    # 获取 stdout_file 的父目录
    parent_dir = os.path.dirname(stdout_file)
    
    # 生成新的文件路径
    custom_path = os.path.join(parent_dir, custom_filename)
    
    return custom_path

class Case:
    def __init__(self, name: str, cmd: str, pid: int, monitor_file: str, conn: Connection, proc) -> None:
        self.name = name
        self.cmd = cmd
        self.pid = pid
        self.monitor_file = monitor_file
        self.conn = conn
        self.code = None
        self.proc = proc
        self.start_time = time.time()
        self.elapsed_time = 0.0
    
    def stop(self):
        if self.start_time is not None:
            self.elapsed_time += time.time() - self.start_time
            self.start_time = None

    def reset(self):
        self.start_time = None
        self.elapsed_time = 0.0

    def get_elapsed_time(self):
        if self.start_time is not None:
            return self.elapsed_time + (time.time() - self.start_time)
        else:
            return self.elapsed_time
    
    def get_exit_code(self) -> Optional[int]:
        if self.proc.poll() is None:
            return None
        try:
            result = self.conn.run(f'cat {self.monitor_file}', hide=True)
            contents = result.stdout
            if 'exit_code' in contents:
                code = int(contents.split(':')[-1])
                self.code = code
                return code
        except Exception as e:
            print(f"Error retrieving exit code: {e}")
            return None


def search_by_name(cases: List[Case], name: str) -> Optional[Case]:
    """Search for a Case by name in the list of cases."""
    for case in cases:
        if case.name == name:
            return case
    return None

def delete_by_name(cases: List[Case], name: str) -> bool:
    """Delete a Case by name from the list of cases."""
    case_to_delete = search_by_name(cases, name)
    if case_to_delete:
        cases.remove(case_to_delete)
        return True
    return False


class Server2:
    def __init__(self, ip: str) -> None:
        self.ip = ip
        self.username = getpass.getuser()
        self.conn = Connection(host=ip, user=self.username)
        self.cpu_num = int(self.conn.run('cat /proc/cpuinfo| grep "physical id"| sort| uniq| wc -l', hide=True).stdout)
        self.cpu_threads = int(self.conn.run('cat /proc/cpuinfo| grep "processor"| wc -l', hide=True).stdout)
        cores_per_cpu = int(self.conn.run('cat /proc/cpuinfo| grep "cpu cores"| uniq', hide=True).stdout.split(':')[-1])
        self.cpu_cores = cores_per_cpu * self.cpu_num
        self.is_smt = self.cpu_cores < self.cpu_threads
        # print(f'cpu num: {self.cpu_num}, threads: {self.cpu_threads}, cpu_cores: {self.cpu_cores}, is_smt: {self.is_smt}')
        self.success_test: list[Case] = []
        self.failed_test: list[Case] = []
        self.pending_test: list[Case] = []

    def test_connection(self, retries: int = 5, delay: int = 2) -> bool:
        """
        Test the connectivity of the Fabric Connection object.
        If the connection fails, attempt to reconnect up to 'retries' times.
        
        Args:
            retries (int): Number of retry attempts if connection fails. Default is 5.
            delay (int): Delay in seconds between retry attempts. Default is 2 seconds.

        Returns:
            bool: True if connection is successful, False if all attempts fail.
        """
        attempt = 0
        
        while attempt <= retries:
            try:
                # Use a simple command to test the connection, like 'uname' to get the system name
                result = self.conn.run('uname', hide=True)
                if result.ok:
                    print("Connection successful.")
                    return True
            except Exception as e:
                print(f"Connection attempt {attempt + 1}/{retries + 1} failed: {e}")
                attempt += 1
                if attempt <= retries:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        print("All connection attempts failed.")
        return False
            
    def get_sever_load(self) -> Tuple[float, float, float]:
        load_res = self.conn.run("uptime | grep -oP '(?<=average:).*,.*' ", hide=True).stdout.split(',')
        return tuple([float(i) for i in load_res])
    
    def can_enqueue(self, thread: int, overflow: int = 0) -> bool:
        load_res = self.get_sever_load()
        cpu_cores = self.cpu_cores + overflow
        if load_res[0] + thread < cpu_cores \
            and load_res[1] + thread < cpu_cores and load_res[2] + thread < cpu_cores:
            return True
        else:
            return False

    def check_running(self):
        for case in self.pending_test:
            res = case.get_exit_code()
            if res is not None:
                self.pending_test.remove(res)
                if res != 0:
                    print(f"[ERROR] {case.name} exit with code {res}")
                    self.failed_test.append()
                else:
                    self.success_test.append()

    def assign(self, test_name: str, cmd: str, xs_path: str, stdout_file: str, stderr_file: str, threads: int = 16) -> bool:
        self.check_running()
        if self.get_sever_load()[0] > self.cpu_cores + self.cpu_cores/5:
            return False
        moniter_file = generate_custom_path(stdout_file, 'moniter.txt')
        pwd = os.path.dirname(os.path.abspath(__file__))
        run_args = generate_command_args_shell(test_name, cmd, threads, xs_path, moniter_file, stdout_file, stderr_file)
        command = f'ssh {self.username}@{self.ip} "python {pwd}/task.py {run_args}"'
        print(command)
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid, shell=True)
        while True:
            time.sleep(1)
            res = proc.stdout.readline().decode()
            print(res)
            try:
                pid = int(res)
                break
            except Exception:
                pass
        case_ = Case(test_name, cmd, pid, moniter_file, self.conn, proc)
        self.pending_test.append(case_)
        return True

        
    def max_free_core(self) -> int:
        # maybe negative
        load_res = self.get_sever_load()
        free_cores = [self.cpu_cores - i for i in load_res]
        return int(min(free_cores))
    
    def cur_tasks_num(self) -> int:
        return len(self.pending_test)
    

if __name__ == "__main__":
    server_list = [
        '172.19.20.3',
        '172.19.20.4',
        '172.19.20.5',
        '172.19.20.6',
        '172.19.20.7',
        '172.19.20.8',
        '172.19.20.9',
        '172.19.20.20',
        '172.19.20.21',
        '172.19.20.22',
        '172.19.20.23',
        '172.19.20.24',
        '172.19.20.25',
        '172.19.20.26',
        '172.19.20.27',
        '172.19.20.28',
    ]
    servers = []
    for ip in server_list:
        s = Server2(ip)
        servers.append(s)
        print(f'ip: {ip}, avg load: {s.get_sever_load()}, can_enqueue: {s.can_enqueue(16)}, free_cores: {s.max_free_core()}')
        s.assign('123', 'sleep 10 && echo 30', '123', f'{ip}out.txt', f'{ip}err.txt')
        
