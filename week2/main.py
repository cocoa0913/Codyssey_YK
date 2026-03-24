def read_csv(filename):
    data = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(line.split(','))
    except FileNotFoundError:
        print(f'Error: {filename} 파일을 찾을 수 없습니다.')
    except OSError as e:
        print(f'Error: {filename} 파일 읽기 실패 - {e}')
    return data


def print_inventory(inventory):
    for row in inventory:
        print(', '.join(row))


def sort_by_flammability(inventory):
    # 새 리스트 생성 없이 원본 in-place 정렬
    try:
        inventory[1:] = sorted(inventory[1:], key=lambda x: float(x[4]), reverse=True)
    except (ValueError, IndexError) as e:
        print(f'Error: 정렬 중 오류 발생 - {e}')


def filter_dangerous(inventory):
    if not inventory:
        return []
    header = inventory[0]
    dangerous = [header]
    for row in inventory[1:]:
        try:
            if float(row[4]) >= 0.7:
                dangerous.append(row)
        except (ValueError, IndexError):
            pass
    return dangerous


def save_csv(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for row in data:
                f.write(','.join(row) + '\n')
        print(f'\n{filename} 저장 완료.')
    except OSError as e:
        print(f'Error: {filename} 저장 실패 - {e}')


def save_binary(filename, data):
    try:
        with open(filename, 'wb') as f:
            f.write(len(data).to_bytes(4, 'big'))
            for row in data:
                f.write(len(row).to_bytes(2, 'big'))
                for field in row:
                    encoded = field.encode('utf-8')
                    f.write(len(encoded).to_bytes(2, 'big'))
                    f.write(encoded)
        print(f'{filename} 저장 완료.')
    except OSError as e:
        print(f'Error: {filename} 저장 실패 - {e}')


def read_binary(filename):
    data = []
    try:
        with open(filename, 'rb') as f:
            row_count = int.from_bytes(f.read(4), 'big')
            for _ in range(row_count):
                field_count = int.from_bytes(f.read(2), 'big')
                row = []
                for _ in range(field_count):
                    field_len = int.from_bytes(f.read(2), 'big')
                    field = f.read(field_len).decode('utf-8')
                    row.append(field)
                data.append(row)
    except FileNotFoundError:
        print(f'Error: {filename} 파일을 찾을 수 없습니다.')
    except (UnicodeDecodeError, ValueError) as e:
        print(f'Error: {filename} 디코딩 실패 - {e}')
    except OSError as e:
        print(f'Error: {filename} 파일 읽기 실패 - {e}')
    return data


def main():
    csv_file = 'Mars_Base_Inventory_List.csv'

    # 1. CSV 읽기 및 출력
    print('=== 화성 기지 입고 물질 목록 ===')
    inventory = read_csv(csv_file)
    if not inventory:
        print('Error: 데이터가 없어 프로그램을 종료합니다.')
        return
    print_inventory(inventory)

    # 2. 인화성 높은 순으로 in-place 정렬 (sorted_inventory 별도 변수 없음)
    sort_by_flammability(inventory)
    print('\n=== 인화성 순 정렬 목록 ===')
    print_inventory(inventory)

    # 보너스: 정렬된 전체 목록 이진 파일 저장
    save_binary('Mars_Base_Inventory_List.bin', inventory)

    # 3. 인화성 지수 0.7 이상 필터링
    dangerous = filter_dangerous(inventory)
    del inventory  # 전체 목록 즉시 해제

    print('\n=== 인화성 위험 물질 목록 (0.7 이상) ===')
    print_inventory(dangerous)

    # 4. 위험 물질 목록 CSV 저장
    save_csv('Mars_Base_Inventory_danger.csv', dangerous)
    del dangerous  # 위험 목록 즉시 해제

    # 보너스: 이진 파일 읽기 및 출력
    print('\n=== 이진 파일에서 읽은 목록 ===')
    binary_data = read_binary('Mars_Base_Inventory_List.bin')
    print_inventory(binary_data)
    del binary_data


if __name__ == '__main__':
    main()
