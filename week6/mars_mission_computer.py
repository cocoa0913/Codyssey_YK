import json
import platform
import os
import ctypes


SETTING_FILE = 'setting.txt'


def _get_windows_memory_status():
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ('dwLength', ctypes.c_ulong),
            ('dwMemoryLoad', ctypes.c_ulong),
            ('ullTotalPhys', ctypes.c_ulonglong),
            ('ullAvailPhys', ctypes.c_ulonglong),
            ('ullTotalPageFile', ctypes.c_ulonglong),
            ('ullAvailPageFile', ctypes.c_ulonglong),
            ('ullTotalVirtual', ctypes.c_ulonglong),
            ('ullAvailVirtual', ctypes.c_ulonglong),
            ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
        ]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    return status


def _load_settings(path=SETTING_FILE):
    default = {
        'info': {
            'operating_system': True,
            'os_version': True,
            'cpu_type': True,
            'cpu_cores': True,
            'memory_size': True,
        },
        'load': {
            'cpu_usage': True,
            'memory_usage': True,
        },
    }

    try:
        with open(path, 'r', encoding='utf-8') as f:
            section = None
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    section = line[1:-1].strip()
                    continue
                if section in default and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().lower()
                    if key in default[section]:
                        default[section][key] = (value == 'true')
    except FileNotFoundError:
        pass
    except Exception as e:
        print('Failed to read setting file: ' + str(e))

    return default


class MissionComputer:

    def __init__(self):
        self.settings = _load_settings()

    def get_mission_computer_info(self):
        try:
            candidates = {
                'operating_system': platform.system(),
                'os_version': platform.version(),
                'cpu_type': platform.processor(),
                'cpu_cores': os.cpu_count(),
                'memory_size': self._format_memory_size(
                    self._get_memory_size()
                ),
            }
            enabled = self.settings.get('info', {})
            info = {
                key: value for key, value in candidates.items()
                if enabled.get(key, True)
            }
        except Exception as e:
            print('Error getting system info: ' + str(e))
            info = {}

        print(json.dumps(info, indent=4, ensure_ascii=False))
        return info

    def get_mission_computer_load(self):
        try:
            candidates = {
                'cpu_usage': self._format_percent(self._get_cpu_usage()),
                'memory_usage': self._format_percent(self._get_memory_usage()),
            }
            enabled = self.settings.get('load', {})
            load = {
                key: value for key, value in candidates.items()
                if enabled.get(key, True)
            }
        except Exception as e:
            print('Error getting system load: ' + str(e))
            load = {}

        print(json.dumps(load, indent=4, ensure_ascii=False))
        return load

    def _get_memory_size(self):
        try:
            if platform.system() == 'Windows':
                status = _get_windows_memory_status()
                return int(status.ullTotalPhys)
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal'):
                        kb = int(line.split()[1])
                        return kb * 1024
        except Exception as e:
            return 'unknown (' + str(e) + ')'
        return 'unknown'

    def _get_cpu_usage(self):
        try:
            if platform.system() == 'Windows':
                import subprocess
                result = subprocess.run(
                    [
                        'powershell', '-NoProfile', '-Command',
                        '(Get-CimInstance Win32_Processor | '
                        'Measure-Object -Property LoadPercentage '
                        '-Average).Average'
                    ],
                    capture_output=True, text=True, timeout=5,
                )
                output = result.stdout.strip()
                if output:
                    return round(float(output), 2)
                return 'unknown'
            import time
            with open('/proc/stat', 'r') as f:
                times1 = list(map(int, f.readline().split()[1:]))
            time.sleep(0.1)
            with open('/proc/stat', 'r') as f:
                times2 = list(map(int, f.readline().split()[1:]))
            idle_delta = times2[3] - times1[3]
            total_delta = sum(times2) - sum(times1)
            if total_delta <= 0:
                return 'unknown'
            return round((1 - idle_delta / total_delta) * 100, 2)
        except Exception as e:
            return 'unknown (' + str(e) + ')'

    def _get_memory_usage(self):
        try:
            if platform.system() == 'Windows':
                status = _get_windows_memory_status()
                return float(status.dwMemoryLoad)
            meminfo = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split()
                    meminfo[parts[0].rstrip(':')] = int(parts[1])
            total = meminfo.get('MemTotal', 0)
            available = meminfo.get('MemAvailable', 0)
            if total > 0:
                return round((total - available) / total * 100, 2)
        except Exception as e:
            return 'unknown (' + str(e) + ')'
        return 'unknown'

    def _format_memory_size(self, value):
        if not isinstance(value, int):
            return value
        gib = value / (1024 ** 3)
        return str(value) + ' bytes (' + format(gib, '.2f') + ' GiB)'

    def _format_percent(self, value):
        if isinstance(value, (int, float)):
            return format(value, '.2f') + ' %'
        return value


if __name__ == '__main__':
    runComputer = MissionComputer()
    print('--- Mission Computer Info ---')
    runComputer.get_mission_computer_info()
    print('--- Mission Computer Load ---')
    runComputer.get_mission_computer_load()
