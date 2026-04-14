import json
import platform
import os
import ctypes


def _get_windows_memory_status():
    class MEMORYSTATUS(ctypes.Structure):
        _fields_ = [
            ('dwLength', ctypes.c_ulong),
            ('dwMemoryLoad', ctypes.c_ulong),
            ('dwTotalPhys', ctypes.c_ulong),
            ('dwAvailPhys', ctypes.c_ulong),
            ('dwTotalPageFile', ctypes.c_ulong),
            ('dwAvailPageFile', ctypes.c_ulong),
            ('dwTotalVirtual', ctypes.c_ulong),
            ('dwAvailVirtual', ctypes.c_ulong),
        ]

    status = MEMORYSTATUS()
    status.dwLength = ctypes.sizeof(MEMORYSTATUS)
    ctypes.windll.kernel32.GlobalMemoryStatus(ctypes.byref(status))
    return status


class MissionComputer:

    def get_mission_computer_info(self):
        try:
            info = {
                'operating_system': platform.system(),
                'os_version': platform.version(),
                'cpu_type': platform.processor(),
                'cpu_cores': os.cpu_count(),
                'memory_size_bytes': self._get_memory_size(),
            }
        except Exception as e:
            print(f'Error getting system info: {e}')
            info = {}

        print(json.dumps(info, indent=4))

    def get_mission_computer_load(self):
        try:
            load = {
                'cpu_usage_percent': self._get_cpu_usage(),
                'memory_usage_percent': self._get_memory_usage(),
            }
        except Exception as e:
            print(f'Error getting system load: {e}')
            load = {}

        print(json.dumps(load, indent=4))

    def _get_memory_size(self):
        try:
            if platform.system() == 'Windows':
                status = _get_windows_memory_status()
                return status.dwTotalPhys
            else:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemTotal'):
                            kb = int(line.split()[1])
                            return kb * 1024
        except Exception as e:
            return f'unknown ({e})'

    def _get_cpu_usage(self):
        try:
            if platform.system() == 'Windows':
                import subprocess
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'loadpercentage'],
                    capture_output=True, text=True
                )
                lines = [line.strip() for line in result.stdout.strip().splitlines()
                         if line.strip()]
                if len(lines) >= 2:
                    return float(lines[1])
            else:
                import time
                with open('/proc/stat', 'r') as f:
                    times1 = list(map(int, f.readline().split()[1:]))
                time.sleep(0.1)
                with open('/proc/stat', 'r') as f:
                    times2 = list(map(int, f.readline().split()[1:]))
                idle1, idle2 = times1[3], times2[3]
                total1, total2 = sum(times1), sum(times2)
                usage = (1 - (idle2 - idle1) / (total2 - total1)) * 100
                return round(usage, 2)
        except Exception as e:
            return f'unknown ({e})'

    def _get_memory_usage(self):
        try:
            if platform.system() == 'Windows':
                status = _get_windows_memory_status()
                return float(status.dwMemoryLoad)
            else:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = {}
                    for line in f:
                        parts = line.split()
                        meminfo[parts[0].rstrip(':')] = int(parts[1])
                total = meminfo.get('MemTotal', 0)
                available = meminfo.get('MemAvailable', 0)
                if total > 0:
                    return round((total - available) / total * 100, 2)
        except Exception as e:
            return f'unknown ({e})'


runComputer = MissionComputer()
runComputer.get_mission_computer_info()
runComputer.get_mission_computer_load()
