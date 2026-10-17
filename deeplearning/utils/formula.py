"""训练执行与代码导出共享的公式语法验证，不依赖 PyTorch。"""
import ast

FUNCTIONS = {"sin", "cos", "tanh", "sigmoid", "relu", "exp", "log", "sqrt", "abs"}


def validate_formula(formula):
    expression = (formula or "x @ w + b").strip()
    if expression.startswith("y") and "=" in expression:
        left, right = expression.split("=", 1)
        if left.strip() == "y":
            expression = right.strip()
    if len(expression) > 500 or "\n" in expression or "\r" in expression:
        raise ValueError("公式必须为一行，最多 500 字符")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        raise ValueError("公式格式不正确")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult,
               ast.Div, ast.Pow, ast.MatMult, ast.UAdd, ast.USub, ast.Name,
               ast.Load, ast.Call, ast.Constant)
    nodes = list(ast.walk(tree))
    if len(nodes) > 150:
        raise ValueError("公式过于复杂")
    for node in nodes:
        if not isinstance(node, allowed):
            raise ValueError("公式包含不支持的语法")
        if isinstance(node, ast.Name) and node.id not in {"x", "w", "b", "pi"} | FUNCTIONS:
            raise ValueError("公式中只能使用 x、w、b、pi 和允许的数学函数")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name)
                or node.func.id not in FUNCTIONS or node.keywords):
            raise ValueError("只能调用允许的数学函数")
        if isinstance(node, ast.Constant) and (type(node.value) not in (int, float) or abs(node.value) > 1e6):
            raise ValueError("公式常量必须为范围内的数字")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            if not isinstance(node.right, ast.Constant) or abs(node.right.value) > 10:
                raise ValueError("公式指数必须是绝对值不大于 10 的数字")
    return expression
