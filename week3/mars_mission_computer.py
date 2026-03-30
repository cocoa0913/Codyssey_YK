class DummySensor:
    ENV_RANGES = {
        'mars_base_internal_temperature': (18, 30),
        'mars_base_external_temperature': (0, 21),
        'mars_base_internal_humidity': (50, 60),
        'mars_base_external_illuminance': (500, 715),
        'mars_base_internal_co2': (0.02, 0.1),
        'mars_base_internal_oxygen': (4, 7),
    }

    LOG_FILE = __file__.replace('\\', '/').rsplit('/', 1)[0] + '/sensor_log.log'
    LOG_HEADER = (
        'datetime, '
        'mars_base_internal_temperature, '
        'mars_base_external_temperature, '
        'mars_base_internal_humidity, '
        'mars_base_external_illuminance, '
        'mars_base_internal_co2, '
        'mars_base_internal_oxygen'
    )

    # LCG (Linear Congruential Generator) parameters (Numerical Recipes)
    _LCG_A = 1664525
    _LCG_C = 1013904223

    __slots__ = ('env_values', '_seed')

    def __init__(self):
        self.env_values = {key: 0 for key in self.ENV_RANGES}
        self._seed = id(object()) & 0xFFFFFFFF

    def _rand(self):
        self._seed = (self._LCG_A * self._seed + self._LCG_C) & 0xFFFFFFFF
        return self._seed / 0xFFFFFFFF

    def _uniform(self, low, high):
        return low + (high - low) * self._rand()

    def set_env(self):
        for key, (low, high) in self.ENV_RANGES.items():
            self.env_values[key] = round(self._uniform(low, high), 4)

    def get_env(self):
        self._write_log()
        return self.env_values

    def _write_log(self):
        now = input('현재 날짜와 시간을 입력하세요 (YYYY-MM-DD HH:MM:SS): ')
        log_line = (
            f'{now}, '
            f'{self.env_values["mars_base_internal_temperature"]}, '
            f'{self.env_values["mars_base_external_temperature"]}, '
            f'{self.env_values["mars_base_internal_humidity"]}, '
            f'{self.env_values["mars_base_external_illuminance"]}, '
            f'{self.env_values["mars_base_internal_co2"]}, '
            f'{self.env_values["mars_base_internal_oxygen"]}\n'
        )
        try:
            with open(self.LOG_FILE, 'r'):
                write_header = False
        except FileNotFoundError:
            write_header = True
        with open(self.LOG_FILE, 'a') as f:
            if write_header:
                f.write(self.LOG_HEADER + '\n')
            f.write(log_line)


ds = DummySensor()
ds.set_env()
print(ds.get_env())
