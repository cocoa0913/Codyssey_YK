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

FONT_SIZE_DEFAULT = 64  # 표시 문자 8자 이하
FONT_SIZE_MEDIUM = 52   # 표시 문자 9~11자
FONT_SIZE_SMALL = 40    # 표시 문자 12자 이상

MAX_DIGITS = 9          # 입력 가능한 최대 자릿수 (부호·소수점 제외)
MAX_VALUE = 1e15        # 처리 가능한 최대 절댓값


class Calculator:
    """계산기 핵심 로직 클래스."""

    def __init__(self):
        self.current_input = '0'   # 현재 입력 중인 숫자 문자열
        self.previous_input = ''   # 연산자 입력 전 저장된 숫자 문자열
        self.operator = ''         # 선택된 연산자 (÷ × − +)
        self.reset_next = False    # 다음 숫자 입력 시 현재 값 초기화 여부

    def input_digit(self, digit):
        """숫자 키 입력 처리: 화면에 숫자를 누적한다."""
        if self.reset_next or self.current_input == '0':
            self.current_input = digit
            self.reset_next = False
        elif len(self.current_input.replace('-', '').replace('.', '')) < MAX_DIGITS:
            self.current_input += digit

    def input_decimal(self):
        """소수점 키 입력 처리: 이미 소수점이 있으면 추가하지 않는다."""
        if self.reset_next:
            self.current_input = '0.'
            self.reset_next = False
        elif '.' not in self.current_input:
            self.current_input += '.'

    def set_operator(self, op):
        """연산자 선택: 이전 연산이 있으면 먼저 계산 후 새 연산자를 저장한다."""
        if self.current_input == 'Error':
            return
        if self.operator and not self.reset_next and self.previous_input:
            self.equal()
            self.reset_next = False
        if self.current_input == 'Error':
            return
        self.previous_input = self.current_input
        self.operator = op
        self.reset_next = True

    # ── 사칙 연산 메소드 ──────────────────────────────────────

    def add(self, a, b):
        """덧셈."""
        return a + b

    def subtract(self, a, b):
        """뺄셈."""
        return a - b

    def multiply(self, a, b):
        """곱셈."""
        return a * b

    def divide(self, a, b):
        """나눗셈. 0으로 나누면 ZeroDivisionError 발생."""
        if b == 0:
            raise ZeroDivisionError('Cannot divide by zero')
        return a / b

    # ── 초기화 / 부호 / 퍼센트 메소드 ──────────────────────────

    def reset(self):
        """모든 상태를 초기값으로 리셋한다."""
        self.current_input = '0'
        self.previous_input = ''
        self.operator = ''
        self.reset_next = False

    def negative_positive(self):
        """현재 입력값의 양수/음수를 전환한다."""
        if self.current_input in ('0', 'Error'):
            return
        if self.current_input.startswith('-'):
            self.current_input = self.current_input[1:]
        else:
            self.current_input = '-' + self.current_input

    def percent(self):
        """현재 입력값을 100으로 나눠 퍼센트 값으로 변환한다."""
        try:
            value = float(self.current_input)
            self.current_input = self._format_result(value / 100)
        except ValueError:
            self.current_input = 'Error'

    # ── 결과 출력 메소드 ─────────────────────────────────────

    def equal(self):
        """저장된 연산자로 계산을 수행하고 결과를 current_input에 저장한다."""
        if not self.operator or not self.previous_input:
            return
        try:
            a = float(self.previous_input)
            b = float(self.current_input)
            op_map = {
                '+': self.add,
                '−': self.subtract,
                '×': self.multiply,
                '÷': self.divide,
            }
            result = op_map[self.operator](a, b)
            if abs(result) >= MAX_VALUE:
                self.current_input = 'Error'
            else:
                self.current_input = self._format_result(result)
        except (ValueError, ZeroDivisionError):
            self.current_input = 'Error'
        finally:
            self.previous_input = ''
            self.operator = ''
            self.reset_next = True

    def _format_result(self, value):
        """결과값을 문자열로 변환한다. 소수점 6자리 초과 시 반올림한다."""
        if value == int(value):
            return str(int(value))
        rounded = round(value, 6)   # 보너스: 소수점 6자리 이하로 반올림
        if rounded == int(rounded):
            return str(int(rounded))
        return str(rounded)


class CalculatorApp(QWidget):
    """계산기 UI 클래스. Calculator 클래스와 연결되어 동작한다."""

    def __init__(self):
        super().__init__()
        self.calc = Calculator()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Calculator')
        self.setStyleSheet('background-color: #1c1c1c;')
        self.setFixedSize(600, 1100)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setContentsMargins(16, 16, 16, 16)

        self.display = QLabel('0')
        self.display.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.display.setFont(QFont('Arial', FONT_SIZE_DEFAULT, QFont.Light))
        self.display.setStyleSheet('color: white; padding: 0px 12px 16px 12px;')
        self.display.setFixedHeight(260)
        grid.addWidget(self.display, 0, 0, 1, 4)

        buttons = [
            ('AC',  1, 0, 1, '#d4d4d2', '#000000'),
            ('+/-', 1, 1, 1, '#d4d4d2', '#000000'),
            ('%',   1, 2, 1, '#d4d4d2', '#000000'),
            ('÷',   1, 3, 1, '#ff9500', '#ffffff'),
            ('7',   2, 0, 1, '#505050', '#ffffff'),
            ('8',   2, 1, 1, '#505050', '#ffffff'),
            ('9',   2, 2, 1, '#505050', '#ffffff'),
            ('×',   2, 3, 1, '#ff9500', '#ffffff'),
            ('4',   3, 0, 1, '#505050', '#ffffff'),
            ('5',   3, 1, 1, '#505050', '#ffffff'),
            ('6',   3, 2, 1, '#505050', '#ffffff'),
            ('−',   3, 3, 1, '#ff9500', '#ffffff'),
            ('1',   4, 0, 1, '#505050', '#ffffff'),
            ('2',   4, 1, 1, '#505050', '#ffffff'),
            ('3',   4, 2, 1, '#505050', '#ffffff'),
            ('+',   4, 3, 1, '#ff9500', '#ffffff'),
            ('0',   5, 0, 2, '#505050', '#ffffff'),
            ('.',   5, 2, 1, '#505050', '#ffffff'),
            ('=',   5, 3, 1, '#ff9500', '#ffffff'),
        ]

        for label, row, col, colspan, bg, fg in buttons:
            btn = self._create_button(label, bg, fg, colspan)
            btn.clicked.connect(
                lambda checked, t=label: self.on_button_click(t)
            )
            grid.addWidget(btn, row, col, 1, colspan)

        self.setLayout(grid)

    def _create_button(self, label, bg_color, fg_color, colspan):
        btn = QPushButton(label)
        btn.setFont(QFont('Arial', 30))
        btn.setFixedHeight(112)

        align_style = (
            'text-align: left; padding-left: 40px;' if colspan == 2
            else 'text-align: center;'
        )
        btn.setStyleSheet(
            f'QPushButton {{'
            f'  background-color: {bg_color};'
            f'  color: {fg_color};'
            f'  border-radius: 56px;'
            f'  {align_style}'
            f'}}'
        )
        return btn

    def on_button_click(self, text):
        """버튼 클릭 이벤트: Calculator 클래스의 해당 메소드를 호출한다."""
        if text.isdigit():
            self.calc.input_digit(text)
        elif text == '.':
            self.calc.input_decimal()
        elif text == 'AC':
            self.calc.reset()
        elif text in ('÷', '×', '−', '+'):
            self.calc.set_operator(text)
        elif text == '=':
            self.calc.equal()
        elif text == '+/-':
            self.calc.negative_positive()
        elif text == '%':
            self.calc.percent()
        self._update_display()

    def _format_display(self, value_str):
        """숫자 문자열에 3자리마다 쉼표를 붙인 표시용 문자열로 변환한다."""
        if '.' in value_str:
            integer_part, decimal_part = value_str.split('.')
        else:
            integer_part, decimal_part = value_str, None

        sign = '-' if integer_part.startswith('-') else ''
        abs_integer = integer_part.lstrip('-')
        formatted = '{:,}'.format(int(abs_integer))

        if decimal_part is not None:
            return f'{sign}{formatted}.{decimal_part}'
        return f'{sign}{formatted}'

    def _update_display(self):
        """보너스: 표시 문자 수에 따라 폰트 크기를 동적 조절해 전체 내용을 출력한다."""
        text = self.calc.current_input

        if text == 'Error':
            self.display.setText('Error')
            self.display.setFont(QFont('Arial', FONT_SIZE_MEDIUM, QFont.Light))
            return

        display_text = (
            text if text.endswith('.')
            else self._format_display(text)
        )
        self.display.setText(display_text)

        length = len(display_text.replace('-', ''))
        if length >= 12:
            font_size = FONT_SIZE_SMALL
        elif length >= 9:
            font_size = FONT_SIZE_MEDIUM
        else:
            font_size = FONT_SIZE_DEFAULT
        self.display.setFont(QFont('Arial', font_size, QFont.Light))


def main():
    app = QApplication(sys.argv)
    window = CalculatorApp()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
