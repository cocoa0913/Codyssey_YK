import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QPushButton,
    QWidget,
)

# 디스플레이 폰트 크기: 쉼표 포함 표시 문자 수에 따라 3단계로 조절
FONT_SIZE_DEFAULT = 64  # 표시 문자 8자 이하
FONT_SIZE_MEDIUM = 52   # 표시 문자 9~11자
FONT_SIZE_SMALL = 40    # 표시 문자 12자 이상

# 입력 가능한 최대 자릿수 (부호·소수점 제외)
MAX_DIGITS = 9


class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.current_input = '0'    # 현재 입력 중인 숫자 문자열 (내부 저장용, 쉼표 없음)
        self.previous_input = ''    # 연산자 입력 전 저장된 숫자 문자열
        self.operator = ''          # 선택된 연산자 (÷ × − +)
        self.reset_input = False    # 다음 숫자 입력 시 현재 값 초기화 여부
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Calculator')                       # 창 제목 설정
        self.setStyleSheet('background-color: #1c1c1c;')        # 배경색: 어두운 회색
        self.setFixedSize(600, 1100)                            # 창 크기 고정

        grid = QGridLayout()        # 버튼 배치용 그리드 레이아웃 생성
        grid.setSpacing(12)         # 위젯 간 간격
        grid.setContentsMargins(16, 16, 16, 16)  # 레이아웃 외부 여백

        # 숫자 표시 레이블 생성
        self.display = QLabel('0')
        self.display.setAlignment(Qt.AlignRight | Qt.AlignBottom)  # 우측 하단 정렬
        self.display.setFont(QFont('Arial', FONT_SIZE_DEFAULT, QFont.Light))
        self.display.setStyleSheet('color: white; padding: 0px 12px 16px 12px;')
        self.display.setFixedHeight(260)                         # 디스플레이 영역 높이
        grid.addWidget(self.display, 0, 0, 1, 4)                 # 0행, 4열 전체 차지

        # 버튼 정의: (표시 문자, 행, 열, 열 병합 수, 배경색, 글자색)
        buttons = [
            ('AC',  1, 0, 1, '#d4d4d2', '#000000'),  # 전체 초기화
            ('+/-', 1, 1, 1, '#d4d4d2', '#000000'),  # 부호 전환 (미구현)
            ('%',   1, 2, 1, '#d4d4d2', '#000000'),  # 퍼센트 (미구현)
            ('÷',   1, 3, 1, '#ff9500', '#ffffff'),  # 나누기
            ('7',   2, 0, 1, '#505050', '#ffffff'),  # 숫자 7
            ('8',   2, 1, 1, '#505050', '#ffffff'),  # 숫자 8
            ('9',   2, 2, 1, '#505050', '#ffffff'),  # 숫자 9
            ('×',   2, 3, 1, '#ff9500', '#ffffff'),  # 곱하기
            ('4',   3, 0, 1, '#505050', '#ffffff'),  # 숫자 4
            ('5',   3, 1, 1, '#505050', '#ffffff'),  # 숫자 5
            ('6',   3, 2, 1, '#505050', '#ffffff'),  # 숫자 6
            ('−',   3, 3, 1, '#ff9500', '#ffffff'),  # 빼기
            ('1',   4, 0, 1, '#505050', '#ffffff'),  # 숫자 1
            ('2',   4, 1, 1, '#505050', '#ffffff'),  # 숫자 2
            ('3',   4, 2, 1, '#505050', '#ffffff'),  # 숫자 3
            ('+',   4, 3, 1, '#ff9500', '#ffffff'),  # 더하기
            ('0',   5, 0, 2, '#505050', '#ffffff'),  # 숫자 0 (2칸 너비)
            ('.',   5, 2, 1, '#505050', '#ffffff'),  # 소수점
            ('=',   5, 3, 1, '#ff9500', '#ffffff'),  # 계산 실행
        ]

        for label, row, col, colspan, bg, fg in buttons:
            btn = self.create_button(label, bg, fg, colspan)  # 버튼 위젯 생성
            btn.clicked.connect(
                lambda checked, t=label: self.on_button_click(t)  # 클릭 이벤트 연결
            )
            grid.addWidget(btn, row, col, 1, colspan)           # 그리드에 배치

        self.setLayout(grid)  # 레이아웃을 창에 적용

    def create_button(self, label, bg_color, fg_color, colspan):
        btn = QPushButton(label)            # 버튼 텍스트 설정
        btn.setFont(QFont('Arial', 30))     # 버튼 폰트 크기
        btn.setFixedHeight(112)             # 버튼 높이 고정

        # 0 버튼(2칸)은 텍스트를 왼쪽 정렬, 나머지는 가운데 정렬
        if colspan == 2:
            align_style = 'text-align: left; padding-left: 40px;'
        else:
            align_style = 'text-align: center;'

        # 버튼 스타일시트: 배경색, 글자색, 모서리 모양만 설정
        btn.setStyleSheet(
            f'QPushButton {{'
            f'  background-color: {bg_color};'
            f'  color: {fg_color};'
            f'  border-radius: 56px;'       # 원형 모서리
            f'  {align_style}'
            f'}}'
        )
        return btn

    def on_button_click(self, text):
        # 입력된 버튼 종류에 따라 분기 처리
        if text.isdigit():                      # 숫자 버튼
            self.handle_digit(text)
        elif text == '.':                       # 소수점 버튼
            self.handle_decimal()
        elif text == 'AC':                      # 초기화 버튼
            self.handle_clear()
        elif text in ('÷', '×', '−', '+'):     # 연산자 버튼 (보너스: 사칙연산)
            self.handle_operator(text)
        elif text == '=':                       # 계산 실행 버튼 (보너스: 사칙연산)
            self.handle_equals()
        # +/- 와 % 는 UI 버튼만 존재하며 기능 미구현

        self.update_display()  # 버튼 처리 후 디스플레이 갱신

    def handle_digit(self, digit):
        # 연산자 입력 직후이거나 현재 값이 '0'이면 새 숫자로 교체
        if self.reset_input or self.current_input == '0':
            self.current_input = digit
            self.reset_input = False
        elif len(self.current_input.replace('-', '').replace('.', '')) < MAX_DIGITS:
            # 최대 자릿수 미만일 때만 뒤에 추가
            self.current_input += digit

    def handle_decimal(self):
        # 연산자 입력 직후에 소수점을 누르면 '0.'으로 시작
        if self.reset_input:
            self.current_input = '0.'
            self.reset_input = False
        elif '.' not in self.current_input:     # 소수점 중복 입력 방지
            self.current_input += '.'

    def handle_clear(self):
        # 모든 상태를 초기값으로 리셋
        self.current_input = '0'
        self.previous_input = ''
        self.operator = ''
        self.reset_input = False

    def handle_operator(self, op):
        self.previous_input = self.current_input    # 현재 값을 피연산자로 저장
        self.operator = op                          # 연산자 저장
        self.reset_input = True                     # 다음 숫자 입력 시 초기화 예약

    def handle_equals(self):
        # 연산자나 이전 값이 없으면 계산하지 않음
        if not self.operator or not self.previous_input:
            return
        try:
            result = self.calculate(
                float(self.previous_input),
                float(self.current_input),
                self.operator
            )
            self.current_input = self.format_result(result)
        except (ValueError, ZeroDivisionError):
            # 변환 오류 또는 0 나누기 예외 처리
            self.current_input = 'Error'
        finally:
            # 계산 완료 후 연산 상태 초기화
            self.previous_input = ''
            self.operator = ''
            self.reset_input = True

    def calculate(self, a, b, op):
        if op == '÷':
            if b == 0:
                raise ZeroDivisionError('Cannot divide by zero')  # 0 나누기 예외 발생
            return a / b
        elif op == '×':
            return a * b
        elif op == '−':
            return a - b
        elif op == '+':
            return a + b
        return 0  # 알 수 없는 연산자일 경우 0 반환

    def format_result(self, value):
        # 정수로 표현 가능하면 소수점 제거, 아니면 소수 8자리까지 반올림
        if value == int(value):
            return str(int(value))
        return str(round(value, 8))

    def format_display(self, value_str):
        # 내부 숫자 문자열을 3자리마다 쉼표를 붙인 표시용 문자열로 변환
        if '.' in value_str:
            integer_part, decimal_part = value_str.split('.')   # 정수부와 소수부 분리
        else:
            integer_part, decimal_part = value_str, None

        # 부호 분리 후 정수부에 쉼표 삽입
        sign = '-' if integer_part.startswith('-') else ''
        abs_integer = integer_part.lstrip('-')                  # 부호 제거
        formatted = '{:,}'.format(int(abs_integer))             # 3자리마다 쉼표 삽입

        if decimal_part is not None:
            return f'{sign}{formatted}.{decimal_part}'          # 소수부 재결합
        return f'{sign}{formatted}'

    def update_display(self):
        # 'Error' 상태는 쉼표 변환 없이 그대로 표시
        if self.current_input == 'Error':
            self.display.setText('Error')
            self.display.setFont(QFont('Arial', FONT_SIZE_MEDIUM, QFont.Light))
            return

        # 소수점만 입력 중일 때는 쉼표 변환 없이 그대로 표시 (예: '0.')
        if self.current_input.endswith('.'):
            display_text = self.current_input
        else:
            display_text = self.format_display(self.current_input)  # 쉼표 포함 문자열로 변환

        self.display.setText(display_text)  # 디스플레이에 포맷된 값 출력

        # 표시 문자 수에 따라 폰트 크기 동적 조절
        length = len(display_text.replace('-', ''))
        if length >= 12:
            self.display.setFont(QFont('Arial', FONT_SIZE_SMALL, QFont.Light))
        elif length >= 9:
            self.display.setFont(QFont('Arial', FONT_SIZE_MEDIUM, QFont.Light))
        else:
            self.display.setFont(QFont('Arial', FONT_SIZE_DEFAULT, QFont.Light))


def main():
    app = QApplication(sys.argv)    # Qt 애플리케이션 객체 생성
    window = Calculator()           # 계산기 위젯 생성
    window.show()                   # 창 표시
    app.exec_()                     # 이벤트 루프 실행


if __name__ == '__main__':
    main()
