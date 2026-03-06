"""Unit tests for CalculatorTool — no API calls required."""

import pytest
from tools.calculator_tool import CalculatorTool


@pytest.fixture
def calc():
    return CalculatorTool()


class TestBasicArithmetic:
    def test_addition(self, calc):
        assert "= 5" in calc.execute("2 + 3")

    def test_subtraction(self, calc):
        assert "= 7" in calc.execute("10 - 3")

    def test_multiplication(self, calc):
        assert "= 20" in calc.execute("4 * 5")

    def test_division(self, calc):
        assert "= 5.0" in calc.execute("10 / 2")

    def test_power(self, calc):
        assert "= 8" in calc.execute("2 ** 3")

    def test_modulo(self, calc):
        assert "= 1" in calc.execute("10 % 3")

    def test_negative(self, calc):
        assert "= -5" in calc.execute("-5")

    def test_complex_expression(self, calc):
        result = calc.execute("96.8 / 383.3 * 100")
        assert "= " in result
        value = float(result.split("= ")[1])
        assert abs(value - 25.24) < 0.1


class TestFunctions:
    def test_sqrt(self, calc):
        assert "= 12.0" in calc.execute("sqrt(144)")

    def test_abs(self, calc):
        assert "= 42" in calc.execute("abs(-42)")

    def test_round(self, calc):
        assert "= 3" in calc.execute("round(3.14)")

    def test_min(self, calc):
        assert "= 1" in calc.execute("min(3, 1, 2)")

    def test_max(self, calc):
        assert "= 99" in calc.execute("max(1, 99, 50)")

    def test_sum(self, calc):
        assert "= 15" in calc.execute("sum([1, 2, 3, 4, 5])")

    def test_log10(self, calc):
        assert "= 2.0" in calc.execute("log10(100)")


class TestSafety:
    """The calculator must reject anything beyond whitelisted operations."""

    def test_rejects_strings(self, calc):
        result = calc.execute("'hello'")
        assert "error" in result.lower()

    def test_rejects_import(self, calc):
        result = calc.execute("__import__('os').system('ls')")
        assert "error" in result.lower()

    def test_rejects_open(self, calc):
        result = calc.execute("open('/etc/passwd')")
        assert "error" in result.lower()

    def test_rejects_exec(self, calc):
        result = calc.execute("exec('print(1)')")
        assert "error" in result.lower()

    def test_division_by_zero(self, calc):
        result = calc.execute("1 / 0")
        assert "error" in result.lower()


class TestToolInterface:
    """Verify the BaseTool interface contract."""

    def test_name(self, calc):
        assert calc.name == "CALCULATOR"

    def test_description_not_empty(self, calc):
        assert len(calc.description) > 10

    def test_execute_returns_string(self, calc):
        assert isinstance(calc.execute("1 + 1"), str)
