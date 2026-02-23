import base64
import io
import re
import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application
)

# 允许的符号/函数（你可以逐步加）
ALLOWED = {
    "pi": sp.pi, "E": sp.E,
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "log": sp.log, "ln": sp.log, "exp": sp.exp,
    "sqrt": sp.sqrt, "Abs": sp.Abs,
}

TRANSFORMS = standard_transformations + (implicit_multiplication_application,)

FORBIDDEN = re.compile(r"(__|import|exec|eval|lambda|open|os\.|sys\.|subprocess|pickle)", re.I)

def safe_parse(expr_str: str, extra_locals: dict | None = None) -> sp.Expr:
    if not expr_str or len(expr_str) > 500:
        raise ValueError("表达式为空或过长")
    if FORBIDDEN.search(expr_str):
        raise ValueError("表达式包含不允许的内容")
    local_dict = dict(ALLOWED)
    if extra_locals:
        local_dict.update(extra_locals)

    # 支持 ^ 作为幂：先替换成 **
    expr_str = expr_str.replace("^", "**")

    return parse_expr(expr_str, local_dict=local_dict, transformations=TRANSFORMS, evaluate=True)

def eval_expr(expr_str: str, workspace: dict | None = None):
    workspace = workspace or {}
    expr = safe_parse(expr_str, workspace)
    simplified = sp.simplify(expr)
    return {
        "expr_latex": sp.latex(expr),
        "result_str": str(simplified),
        "result_latex": sp.latex(simplified),
    }

def plot_2d(func_str: str, var_name="x", x_min=-5, x_max=5, n=400, workspace: dict | None = None):
    
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    workspace = workspace or {}
    x = sp.Symbol(var_name, real=True)
    local_ws = dict(workspace)
    local_ws[var_name] = x

    f_expr = safe_parse(func_str, local_ws)

    f = sp.lambdify(x, f_expr, modules=["numpy"])
    xs = np.linspace(float(x_min), float(x_max), int(n))
    ys = f(xs)

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(xs, ys)
    ax.grid(True, alpha=0.25)
    ax.set_xlabel(var_name)
    ax.set_ylabel("f({})".format(var_name))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
    return {
        "func_latex": sp.latex(f_expr),
        "img_base64": img_b64,
    }