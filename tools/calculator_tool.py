"""
Safe math evaluator that uses AST parsing instead of eval().

"""

import ast
import math
import operator

from tools.base_tool import BaseTool


class CalculatorTool(BaseTool):

    SAFE_OPERATORS = {
        ast.Add: operator.add,       # 2 + 3
        ast.Sub: operator.sub,       # 5 - 2
        ast.Mult: operator.mul,      # 4 * 3
        ast.Div: operator.truediv,   # 10 / 3
        ast.Pow: operator.pow,       # 2 ** 10
        ast.USub: operator.neg,      # -5
        ast.Mod: operator.mod,       # 10 % 3
    }

    SAFE_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "sqrt": math.sqrt,
        "log": math.log,
        "log10": math.log10,
    }

    @property
    def name(self) -> str:
        return "CALCULATOR"

    @property
    def description(self) -> str:
        return (
            "Evaluate math expressions (revenue ratios, growth percentages, margins). "
            "Supports: +, -, *, /, **, %, abs, round, min, max, sum, sqrt, log, log10."
        )

    def execute(self, tool_input: str, **kwargs) -> str:
        """Parse and evaluate a math expression.

        Args:
            tool_input: A math expression string like "96.8 / 383.3 * 100".
            **kwargs: Ignored. Calculator doesn't need role or other context.

        Returns:
            A string like "96.8 / 383.3 * 100 = 25.24", or an error message
            if the expression is invalid or uses unsupported operations.
        """
        try:
            tree = ast.parse(tool_input.strip(), mode="eval")
            result = self.evaluate(tree)
            return f"{tool_input.strip()} = {result}"
        except Exception as e:
            return f"Calculator error: {e}. Provide a valid math expression."

    def evaluate(self, node: ast.AST):
        """Recursively walk an AST node and compute the result.

        Args:
            node: An ast.AST node from ast.parse().

        Returns:
            The computed numeric result (int or float).

        Raises:
            ValueError: If the node type or operation isn't in the whitelist.
        """
        # Outer wrapper from ast.parse(mode="eval") — unwrap and evaluate body
        if isinstance(node, ast.Expression):
            return self.evaluate(node.body)

        # Numbers (int/float). Rejects strings or other constants.
        # e.g. 96.8 → return 96.8
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

        # Binary operations: +, -, *, /, **, %
        # Recursively evaluates left and right, then applies the operator.
        # e.g. 96.8 / 383.3 → evaluate(96.8)=96.8, evaluate(383.3)=383.3, truediv → 0.2524
        if isinstance(node, ast.BinOp):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            op = self.SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(left, right)

        # Unary operations: negative numbers. e.g. -5 → neg(5) → -5
        if isinstance(node, ast.UnaryOp):
            operand = self.evaluate(node.operand)
            op = self.SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(operand)

        # Function calls: only whitelisted functions (sqrt, log, round, etc.).
        # e.g. sqrt(144) → math.sqrt(144) → 12.0
        # Blocks dangerous calls like __import__('os') → ValueError
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.SAFE_FUNCTIONS:
                args = [self.evaluate(arg) for arg in node.args]
                return self.SAFE_FUNCTIONS[node.func.id](*args)
            raise ValueError(f"Unsupported function call: {ast.dump(node.func)}")

        # Lists and tuples: needed for functions like max([10, 20, 30])
        if isinstance(node, ast.List):
            return [self.evaluate(el) for el in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self.evaluate(el) for el in node.elts)

        # Catchall: anything not whitelisted above is rejected
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")
