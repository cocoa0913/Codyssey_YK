import time
import threading


class DummySensor:
    # 화성 기지 환경 센서의 측정 범위 정의
    ENV_RANGES = {
        'mars_base_internal_temperature': (18, 30),      # 내부 온도 (°C)
        'mars_base_external_temperature': (0, 21),       # 외부 온도 (°C)
        'mars_base_internal_humidity': (50, 60),          # 내부 습도 (%)
        'mars_base_external_illuminance': (500, 715),     # 외부 광량 (lux)
        'mars_base_internal_co2': (0.02, 0.1),           # 내부 CO2 농도 (%)
        'mars_base_internal_oxygen': (4, 7),              # 내부 산소 농도 (%)
    }

    # LCG(선형 합동 생성기) 파라미터 - Numerical Recipes 기반
    _LCG_A = 1664525
    _LCG_C = 1013904223
    _LCG_M = 0xFFFFFFFF

    __slots__ = ('env_values', '_seed')

    def __init__(self):
        # 환경값을 0으로 초기화하고, 시드를 객체 메모리 주소 기반으로 설정
        self.env_values = {key: 0 for key in self.ENV_RANGES}
        self._seed = id(object()) & self._LCG_M

    def _rand(self):
        # LCG 알고리즘으로 0~1 사이 의사 난수 생성
        self._seed = (self._LCG_A * self._seed + self._LCG_C) & self._LCG_M
        return self._seed / self._LCG_M

    def _uniform(self, low, high):
        # low~high 범위의 균일 분포 난수 반환
        return low + (high - low) * self._rand()

    def set_env(self):
        # 각 센서 항목에 대해 범위 내 랜덤 값 생성
        for key, (low, high) in self.ENV_RANGES.items():
            self.env_values[key] = round(self._uniform(low, high), 4)

    def get_env(self):
        # 현재 센서 환경값 반환
        return self.env_values


class MissionComputer:
    # 5분 평균 계산 주기 (초)
    _AVG_INTERVAL = 300
    # 센서 데이터 수집 주기 (초)
    _SENSOR_INTERVAL = 5

    def __init__(self):
        # 화성 기지 환경값 저장용 딕셔너리
        self.env_values = dict.fromkeys(DummySensor.ENV_RANGES, 0)
        # 더미 센서 인스턴스
        self.ds = DummySensor()
        self._running = True
        # 5분 평균 계산을 위한 이력 저장소
        self._history = {key: [] for key in self.env_values}
        self._last_avg_time = time.time()

    def get_sensor_data(self):
        # 키 입력 감지용 스레드 시작 (데몬: 메인 종료 시 함께 종료)
        stop_thread = threading.Thread(target=self._wait_for_stop, daemon=True)
        stop_thread.start()

        while self._running:
            # 센서값 갱신 후 가져오기
            self.ds.set_env()
            sensor_data = self.ds.get_env()

            # env_values에 저장하고 이력에 추가
            for key in self.env_values:
                self.env_values[key] = sensor_data[key]
                self._history[key].append(sensor_data[key])

            # JSON 형식으로 현재 환경값 출력
            print(self._to_json(self.env_values))

            # 5분 경과 시 평균값 출력
            if time.time() - self._last_avg_time >= self._AVG_INTERVAL:
                self._print_average()
                self._last_avg_time = time.time()

            time.sleep(self._SENSOR_INTERVAL)

        # 종료 시 마지막 평균값 출력
        self._print_average()
        print('System stoped....')

    def _wait_for_stop(self):
        # 'q' 입력 시 센서 데이터 수집 중지
        while self._running:
            if input().strip().lower() == 'q':
                self._running = False

    def _print_average(self):
        # 이력이 비어 있으면 출력하지 않음
        if not self._history['mars_base_internal_temperature']:
            return

        # 각 환경값의 평균 계산
        avg_values = {}
        for key, values in self._history.items():
            avg_values[key] = round(sum(values) / len(values), 4)

        print('\n5-minute average:')
        print(self._to_json(avg_values))

        # 이력 초기화
        self._history = {key: [] for key in self.env_values}

    @staticmethod
    def _to_json(data):
        # json 모듈 없이 딕셔너리를 JSON 형식 문자열로 변환
        items = list(data.items())
        last_idx = len(items) - 1
        lines = ['{']
        for i, (key, value) in enumerate(items):
            comma = ',' if i < last_idx else ''
            lines.append(f'  \'{key}\': {value}{comma}')
        lines.append('}')
        return '\n'.join(lines)


# MissionComputer를 RunComputer로 인스턴스화하여 센서 데이터 수집 시작
RunComputer = MissionComputer()
RunComputer.get_sensor_data()
