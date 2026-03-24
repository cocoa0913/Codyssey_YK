# CSV 파일을 읽어 2차원 리스트로 반환하는 함수
def read_csv(filename):
    data = []  # 읽어들인 행을 저장할 빈 리스트 초기화
    try:
        with open(filename, 'r', encoding='utf-8') as f:  # UTF-8 인코딩으로 파일을 읽기 모드로 열기
            for line in f:  # 파일을 한 줄씩 순회 (전체를 한번에 메모리에 올리지 않음)
                line = line.strip()  # 줄 앞뒤의 공백 및 개행 문자(\n) 제거
                if line:  # 빈 줄은 건너뜀
                    data.append(line.split(','))  # 쉼표로 분리해 리스트로 만든 뒤 data에 추가
    except FileNotFoundError:  # 파일 경로가 존재하지 않을 때 발생하는 예외 처리
        print(f'Error: {filename} 파일을 찾을 수 없습니다.')
    except OSError as e:  # 권한 부족 등 그 외 파일 I/O 오류 처리
        print(f'Error: {filename} 파일 읽기 실패 - {e}')
    return data  # 파싱된 2차원 리스트 반환


# 2차원 리스트의 각 행을 쉼표+공백으로 이어 출력하는 함수
def print_inventory(inventory):
    for row in inventory:  # 리스트의 각 행을 순회
        print(', '.join(row))  # 행의 요소를 ', '로 연결해 한 줄로 출력


# 인화성 지수(5번째 열, index 4) 기준 내림차순으로 리스트를 in-place 정렬하는 함수
def sort_by_flammability(inventory):
    # inventory[1:]에 sorted 결과를 대입 → 헤더(0번 행)는 그대로 유지하며 원본 리스트 수정
    try:
        inventory[1:] = sorted(inventory[1:], key=lambda x: float(x[4]), reverse=True)
        # lambda x: float(x[4]) → 각 행의 5번째 요소를 float으로 변환해 정렬 기준으로 사용
        # reverse=True → 인화성이 높은 항목이 앞에 오도록 내림차순 정렬
    except (ValueError, IndexError) as e:  # 숫자 변환 실패 또는 열 인덱스 범위 초과 예외 처리
        print(f'Error: 정렬 중 오류 발생 - {e}')


# 인화성 지수 0.7 이상인 행만 추려 새 리스트로 반환하는 함수
def filter_dangerous(inventory):
    if not inventory:  # read_csv 실패 등으로 빈 리스트가 넘어온 경우 → inventory[0]에서 IndexError 방지
        return []
    header = inventory[0]  # 첫 번째 행(헤더)을 별도 보관
    dangerous = [header]  # 반환할 리스트를 헤더로 초기화
    for row in inventory[1:]:  # 헤더를 제외한 데이터 행만 순회
        try:
            if float(row[4]) >= 0.7:  # 인화성 지수를 float으로 변환 후 0.7 이상 여부 확인
                dangerous.append(row)  # 조건을 만족하는 행만 결과 리스트에 추가
        except (ValueError, IndexError):  # 숫자 변환 실패 또는 열 부족 시 해당 행 무시
            pass
    return dangerous  # 헤더 + 위험 물질 행으로 구성된 리스트 반환


# 2차원 리스트를 CSV 형식으로 파일에 저장하는 함수
def save_csv(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:  # UTF-8 인코딩으로 파일을 쓰기 모드로 열기
            for row in data:  # 각 행을 순회
                f.write(','.join(row) + '\n')  # 요소를 쉼표로 연결하고 개행 문자를 붙여 한 줄씩 기록
        print(f'\n{filename} 저장 완료.')
    except OSError as e:  # 쓰기 권한 부족 등 파일 I/O 오류 처리
        print(f'Error: {filename} 저장 실패 - {e}')


# 2차원 리스트를 이진(binary) 파일로 저장하는 함수
def save_binary(filename, data):
    # 커스텀 이진 포맷: [행 수: 4바이트][열 수: 2바이트][필드 길이: 2바이트][필드 데이터: N바이트] ...
    # to_bytes()는 파이썬 내장 메서드 → 라이브러리 import 불필요
    try:
        with open(filename, 'wb') as f:  # 'wb' 모드: 이진 쓰기 모드로 파일 열기
            f.write(len(data).to_bytes(4, 'big'))  # 전체 행 수를 4바이트 빅엔디안으로 기록
            for row in data:
                f.write(len(row).to_bytes(2, 'big'))  # 해당 행의 열 수를 2바이트로 기록
                for field in row:
                    encoded = field.encode('utf-8')  # 필드 문자열을 UTF-8 바이트로 변환
                    f.write(len(encoded).to_bytes(2, 'big'))  # 필드 바이트 길이를 2바이트로 기록
                    f.write(encoded)  # 실제 필드 데이터 기록
        print(f'{filename} 저장 완료.')
    except OSError as e:  # 파일 I/O 오류 처리
        print(f'Error: {filename} 저장 실패 - {e}')


# 이진 파일을 읽어 2차원 리스트로 반환하는 함수
def read_binary(filename):
    # save_binary의 포맷에 맞춰 행 수 → 열 수 → 필드 길이 → 필드 데이터 순으로 파싱
    data = []  # 읽어들인 행을 저장할 빈 리스트 초기화
    try:
        with open(filename, 'rb') as f:  # 'rb' 모드: 이진 읽기 모드로 파일 열기
            row_count = int.from_bytes(f.read(4), 'big')  # 앞 4바이트 → 전체 행 수
            for _ in range(row_count):
                field_count = int.from_bytes(f.read(2), 'big')  # 2바이트 → 열 수
                row = []
                for _ in range(field_count):
                    field_len = int.from_bytes(f.read(2), 'big')  # 2바이트 → 필드 길이
                    field = f.read(field_len).decode('utf-8')  # 해당 길이만큼 읽어 문자열로 디코딩
                    row.append(field)
                data.append(row)
    except FileNotFoundError:  # 파일이 존재하지 않을 때 예외 처리
        print(f'Error: {filename} 파일을 찾을 수 없습니다.')
    except (UnicodeDecodeError, ValueError) as e:  # 디코딩 실패 또는 바이트 파싱 오류 처리
        print(f'Error: {filename} 디코딩 실패 - {e}')
    except OSError as e:  # 그 외 파일 I/O 오류 처리
        print(f'Error: {filename} 파일 읽기 실패 - {e}')
    return data  # 파싱된 2차원 리스트 반환


# 프로그램의 진입점 함수
def main():
    csv_file = 'Mars_Base_Inventory_List.csv'  # 읽어들일 CSV 파일 경로 지정

    # 1. CSV 읽기 및 출력
    print('=== 화성 기지 입고 물질 목록 ===')
    inventory = read_csv(csv_file)  # CSV 파일을 2차원 리스트로 읽기
    if not inventory:  # read_csv가 실패해 빈 리스트를 반환했을 경우 이후 로직에서 크래시 방지
        print('Error: 데이터가 없어 프로그램을 종료합니다.')
        return  # 빈 데이터로 계속 진행하면 filter_dangerous에서 IndexError 발생하므로 조기 종료
    print_inventory(inventory)  # 전체 목록 출력

    # 2. 인화성 높은 순으로 in-place 정렬 (sorted_inventory 별도 변수 없음)
    sort_by_flammability(inventory)  # inventory 원본을 직접 정렬 (새 리스트 생성 없음)
    print('\n=== 인화성 순 정렬 목록 ===')
    print_inventory(inventory)  # 정렬된 전체 목록 출력

    # 보너스: 정렬된 전체 목록 이진 파일 저장
    save_binary('Mars_Base_Inventory_List.bin', inventory)  # 정렬된 데이터를 .bin 파일로 저장

    # 3. 인화성 지수 0.7 이상 필터링
    dangerous = filter_dangerous(inventory)  # 위험 물질만 추려 새 리스트 생성
    del inventory  # 전체 목록은 이후 사용하지 않으므로 즉시 메모리 해제

    print('\n=== 인화성 위험 물질 목록 (0.7 이상) ===')
    print_inventory(dangerous)  # 위험 물질 목록 출력

    # 4. 위험 물질 목록 CSV 저장
    save_csv('Mars_Base_Inventory_danger.csv', dangerous)  # 위험 물질을 별도 CSV로 저장
    del dangerous  # 저장 완료 후 즉시 메모리 해제

    # 보너스: 이진 파일 읽기 및 출력
    print('\n=== 이진 파일에서 읽은 목록 ===')
    binary_data = read_binary('Mars_Base_Inventory_List.bin')  # .bin 파일을 2차원 리스트로 읽기
    print_inventory(binary_data)  # 읽어들인 목록 출력
    del binary_data  # 출력 완료 후 즉시 메모리 해제


if __name__ == '__main__':  # 이 파일이 직접 실행될 때만 main() 호출 (모듈로 import 시에는 실행 안 됨)
    main()


# =============================================================================
# [이진 파일(Binary File) 설명]
# =============================================================================
#
# ── 텍스트 파일 vs 이진 파일 ──────────────────────────────────────────────────
#
# 텍스트 파일 저장 (save_csv — 'w' 모드)
#   저장 내용 예시:
#     Hydrogen,H2,1,Compressed Gas,0.9\n
#   - 사람이 메모장으로 열어도 그대로 읽힘
#   - OS가 개행 문자를 자동 변환함 (\n → Windows에서 \r\n)
#
# 이진 파일 저장 (save_binary — 커스텀 바이너리 포맷)
#   파일 구조 예시 (행이 2개, 각 행이 5개 필드인 경우):
#
#     [00 00 00 02]          ← 행 수 2 (4바이트)
#     [00 05]                ← 첫 번째 행의 열 수 5 (2바이트)
#     [00 08] [48 79 64 72 6F 67 65 6E]  ← 필드 길이 8 + "Hydrogen"
#     [00 02] [48 32]                    ← 필드 길이 2 + "H2"
#     ...
#     [00 05]                ← 두 번째 행의 열 수 5
#     ...
#
#   - 메모장으로 열면 앞부분이 깨진 문자(0x00, 0x02 등)로 보임 → 사람이 읽기 불가
#   - 파서(read_binary)가 없으면 어디서 필드가 끊기는지 알 수 없음
#
# ── 핵심 메서드 ───────────────────────────────────────────────────────────────
#
#   int.to_bytes(length, byteorder)   정수 → 고정 길이 바이트
#     예: (2).to_bytes(2, 'big') → b'\x00\x02'
#
#   int.from_bytes(bytes, byteorder)  바이트 → 정수
#     예: int.from_bytes(b'\x00\x02', 'big') → 2
#
#   str.encode('utf-8')               문자열 → 바이트
#   bytes.decode('utf-8')             바이트 → 문자열
#
#   라이브러리(pickle, struct) 없이 파이썬 내장 메서드만으로 구현 가능.
#
# ── 장단점 비교 ───────────────────────────────────────────────────────────────
#
#   항목          텍스트 파일 (.csv)                이진 파일 (.bin)
#   ──────────    ──────────────────────────────    ──────────────────────────
#   가독성        메모장으로 바로 확인 가능          16진수 편집기 없이는 읽기 불가
#   이식성        OS마다 개행 처리가 달라짐          바이트 그대로 유지, OS 무관
#   안전성        구분자(,)가 데이터에 포함되면       길이 기반 파싱이라 구분자 불필요
#                 파싱 오류 발생 가능
#   이 코드에서   사람이 읽고 편집할 파일            프로그램 간 데이터 전달용
#                 (danger.csv)                      (List.bin)
# =============================================================================
