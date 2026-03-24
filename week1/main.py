def run_mission_recovery():
    log_file = 'mission_computer_main.log'
    problem_file = 'problem_logs.txt'

    # 1. 설치 확인 단계
    print('Hello Mars')

    logs = []
    critical_events = []

    try:
        # 2. 파일을 줄 단위로 읽기 
        with open(log_file, 'r', encoding='utf-8') as f:
            next(f, None)  # 첫 번째 줄(헤더) 소비
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue

                # 위험 요소 식별
                line_lower = line.lower()
                if 'unstable' in line_lower or 'explosion' in line_lower:
                    critical_events.append(line)

                logs.append(line)

    except FileNotFoundError:
        print(f'오류: {log_file} 파일을 찾을 수 없습니다.')
        return
    except PermissionError:
        print(f'오류: {log_file} 파일에 대한 읽기 권한이 없습니다.')
        return
    except UnicodeDecodeError as e:
        print(f'오류: 파일 인코딩 문제가 발생했습니다. ({e})')
        return
    except OSError as e:
        print(f'파일 처리 중 시스템 오류 발생: {e}')
        return

    # 3. 시간의 역순(최신순) 정렬 출력
    if not logs:
        print('로그 데이터가 없습니다.')
        return

    print('\n--- 최신순 정렬 ---')
    for log in reversed(logs):
        print(log)

    # 4. 문제가 되는 부분만 따로 파일로 저장
    try:
        with open(problem_file, 'w', encoding='utf-8') as pf:
            pf.write('--- CRITICAL ACCIDENT LOGS ---\n')
            for event in critical_events:
                pf.write(event + '\n')
    except PermissionError:
        print(f'오류: {problem_file} 파일에 대한 쓰기 권한이 없습니다.')
    except OSError as e:
        print(f'문제 로그 저장 중 오류 발생: {e}')
    else:
        print(f'\n분석 완료: 위험 로그를 {problem_file}에 저장했습니다.')

    print('\n--- 미션 컴퓨터 복구 종료 ---')


if __name__ == '__main__':
    run_mission_recovery()
