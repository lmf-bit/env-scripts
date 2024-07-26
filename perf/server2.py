import getpass
from fabric import Connection


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
        self.success_test = []
        self.failed_test = []
        self.pending_test = []
            
    def get_sever_load(self) -> tuple[float, float, float]:
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
        for running in self.pending_test:
            proc = running[0]
            test = running[1]
            res = proc.poll()
            if res is not None:
                self.pending_test.remove(running)
                if res != 0:
                    print(f"[ERROR] {test} exit with code {proc.returncode}")
                    self.failed_test.append()
                else:
                    self.success_test.append()

    def assign(self, test_name: str, cmd: list[str], xs_path: str, stdout_file: str, stderr_file: str, thread: int = 16):
        pass       
    
        
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
    for ip in server_list:
        s = Server2(ip)
        print(f'ip: {ip}, avg load: {s.get_sever_load()}, can_enqueue: {s.can_enqueue(16)}, free_cores: {s.max_free_core()}')
