# 화성 기지 환경 센서를 흉내내는 가짜(더미) 센서 클래스
class DummySensor:
    # 각 센서 항목이 가질 수 있는 값의 범위 (최솟값, 최댓값)
    ENV_RANGES = {
        'mars_base_internal_temperature': (18, 30),      # 기지 내부 온도 (°C)
        'mars_base_external_temperature': (0, 21),       # 기지 외부 온도 (°C)
        'mars_base_internal_humidity': (50, 60),         # 기지 내부 습도 (%)
        'mars_base_external_illuminance': (500, 715),    # 기지 외부 빛의 양 (W/m²)
        'mars_base_internal_co2': (0.02, 0.1),           # 기지 내부 이산화탄소 농도 (%)
        'mars_base_internal_oxygen': (4, 7),             # 기지 내부 산소 농도 (%)
    }

    # 로그 파일을 저장할 경로 (이 .py 파일과 같은 폴더 안에 sensor_log.log 로 저장)
    LOG_FILE = __file__.replace('\\', '/').rsplit('/', 1)[0] + '/sensor_log.log'
    # 로그 파일 맨 첫 줄에 들어갈 열 이름 (엑셀의 헤더 행과 같은 역할)
    LOG_HEADER = (
        'datetime, '
        'mars_base_internal_temperature, '
        'mars_base_external_temperature, '
        'mars_base_internal_humidity, '
        'mars_base_external_illuminance, '
        'mars_base_internal_co2, '
        'mars_base_internal_oxygen'
    )

    # LCG 난수 생성에 사용하는 숫자들 (Numerical Recipes 교재에서 검증된 값)
    # LCG란 곱하기, 더하기, 나머지 연산만으로 난수를 만드는 간단한 방법이다
    _LCG_A = 1664525        # 곱하는 수
    _LCG_C = 1013904223     # 더하는 수

    # 이 클래스의 인스턴스가 가질 수 있는 변수를 딱 두 개로 제한 (메모리 절약)
    __slots__ = ('env_values', '_seed')

    # 클래스로 객체를 만들 때 자동으로 실행되는 초기화 함수
    def __init__(self):
        # 센서 값을 저장할 딕셔너리, 처음엔 모든 값을 0으로 설정
        self.env_values = {key: 0 for key in self.ENV_RANGES}
        # 난수 생성의 시작점(seed). 실행할 때마다 달라지도록 메모리 주소를 활용
        # id() : 객체 메모리의 주소값 리턴 함수
        # object() : 빈 객체 생성
        # & 0xFFFFFFFF : 계산을 위해 메모리 주소에서 하위 32비트만 잘라냄
        self._seed = id(object()) & 0xFFFFFFFF

    # 0과 1 사이의 난수 한 개를 만들어 돌려주는 함수 (LCG 알고리즘 사용)
    def _rand(self):
        # 현재 seed로 다음 seed를 계산 → 이 과정을 반복하면 난수처럼 보이는 수열이 나옴
        self._seed = (self._LCG_A * self._seed + self._LCG_C) & 0xFFFFFFFF
        # seed를 최댓값으로 나눠서 0~1 사이 소수로 변환
        return self._seed / 0xFFFFFFFF

    # low ~ high 사이의 난수를 만들어 돌려주는 함수
    def _uniform(self, low, high):
        # 0~1 사이 난수를 원하는 범위로 늘려주는 공식
        return low + (high - low) * self._rand()

    # 각 센서 항목에 랜덤 값을 채워 넣는 함수
    def set_env(self):
        # ENV_RANGES에 있는 항목을 하나씩 꺼내서
        for key, (low, high) in self.ENV_RANGES.items():
            # 해당 범위 안의 난수를 소수점 4자리까지 반올림해서 저장
            self.env_values[key] = round(self._uniform(low, high), 4)

    # 현재 센서 값을 돌려주는 함수 (로그 파일에도 기록함)
    def get_env(self):
        self._write_log()       # 로그 파일에 현재 값을 기록
        return self.env_values  # 센서 값 딕셔너리를 반환

    # 날짜/시간과 센서 값을 로그 파일에 한 줄씩 저장하는 함수
    def _write_log(self):
        # 사용자에게 직접 날짜와 시간을 입력받음
        now = input('현재 날짜와 시간을 입력하세요 (YYYY-MM-DD HH:MM:SS): ')
        # 입력받은 시간과 센서 값들을 쉼표로 이어붙여 한 줄짜리 문자열 생성
        log_line = (
            f'{now}, '
            f'{self.env_values["mars_base_internal_temperature"]}, '
            f'{self.env_values["mars_base_external_temperature"]}, '
            f'{self.env_values["mars_base_internal_humidity"]}, '
            f'{self.env_values["mars_base_external_illuminance"]}, '
            f'{self.env_values["mars_base_internal_co2"]}, '
        )
        try:
            # 로그 파일을 읽기 모드로 열어서 이미 존재하는지 확인
            with open(self.LOG_FILE, 'r'):
                write_header = False  # 파일이 있으면 헤더를 다시 쓰지 않음
        except FileNotFoundError:
            write_header = True  # 파일이 없으면 헤더를 맨 처음에 써야 함
        # 로그 파일을 이어쓰기(append) 모드로 열기
        with open(self.LOG_FILE, 'a') as f:
            if write_header:
                f.write(self.LOG_HEADER + '\n')  # 처음 실행할 때만 헤더 한 줄 추가
            f.write(log_line)  # 센서 데이터 한 줄 저장


ds = DummySensor()  # DummySensor 객체 생성
ds.set_env()        # 랜덤 센서 값 채우기
print(ds.get_env()) # 센서 값 출력 (로그 파일에도 저장됨)
