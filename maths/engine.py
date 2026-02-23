import base64
import io
import re
import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application
)

# 允许的符号/函数（你可以逐步扩充）
ALLOWED = {
    "pi": sp.pi, "E": sp.E,
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "log": lambda x, base=10: sp.log(x, base), "ln": sp.log, "exp": sp.exp,
    "sqrt": sp.sqrt, "Abs": sp.Abs,
}

TRANSFORMS = standard_transformations + (implicit_multiplication_application,)
FORBIDDEN = re.compile(r"(__|import|exec|eval|lambda|open|os\.|sys\.|subprocess|pickle)", re.I)

def safe_parse(expr_str: str, extra_locals: dict | None = None) -> sp.Expr:
    if not expr_str or len(expr_str) > 800:
        raise ValueError("表达式为空或过长")
    if FORBIDDEN.search(expr_str):
        raise ValueError("表达式包含不允许的内容")

    local_dict = dict(ALLOWED)
    if extra_locals:
        local_dict.update(extra_locals)

    expr_str = expr_str.replace("^", "**")
    return parse_expr(expr_str, local_dict=local_dict, transformations=TRANSFORMS, evaluate=True)

def _sym(var_name: str) -> sp.Symbol:
    if not var_name or len(var_name) > 8:
        raise ValueError("变量名不合法")
    # 只允许简单变量名
    if not re.fullmatch(r"[a-zA-Z]\w*", var_name):
        raise ValueError("变量名仅支持字母/数字/下划线，且以字母开头")
    return sp.Symbol(var_name, real=True)

def parse_equation(eq_str: str, var: sp.Symbol, workspace: dict | None = None) -> sp.Eq:
    workspace = workspace or {}
    local_ws = dict(workspace)
    local_ws[str(var)] = var

    s = (eq_str or "").strip()
    s = s.replace("^", "**")
    # 支持：x^2-2=0  或  x^2-2  (默认=0)
    if "=" in s:
        parts = s.split("=")
        if len(parts) != 2:
            raise ValueError("方程格式不正确：只能包含一个等号")
        lhs = safe_parse(parts[0], local_ws)
        rhs = safe_parse(parts[1], local_ws)
        return sp.Eq(lhs, rhs)
    else:
        expr = safe_parse(s, local_ws)
        return sp.Eq(expr, 0)

def eval_expr(expr_str: str, workspace: dict | None = None):
    workspace = workspace or {}
    expr = safe_parse(expr_str, workspace)
    simplified = sp.simplify(expr)
    return {
        "kind": "text",
        "expr_latex": sp.latex(expr),
        "result_str": str(simplified),
        "result_latex": sp.latex(simplified),
    }

def simplify_expr(expr_str: str, workspace: dict | None = None):
    workspace = workspace or {}
    expr = safe_parse(expr_str, workspace)
    simplified = sp.simplify(expr)
    return {
        "kind": "text",
        "expr_latex": sp.latex(expr),
        "result_str": str(simplified),
        "result_latex": sp.latex(simplified),
    }

def diff_expr(expr_str: str, var_name="x", order=1, workspace: dict | None = None):
    workspace = workspace or {}
    var = _sym(var_name)
    local_ws = dict(workspace)
    local_ws[var_name] = var
    expr = safe_parse(expr_str, local_ws)

    order = int(order)
    if order < 1 or order > 6:
        raise ValueError("导数阶数建议 1~6")

    d = sp.diff(expr, var, order)
    d_s = sp.simplify(d)
    return {
        "kind": "text",
        "expr_latex": sp.latex(expr),
        "result_str": str(d_s),
        "result_latex": sp.latex(d_s),
    }

def integrate_expr(expr_str: str, var_name="x", a=None, b=None, workspace: dict | None = None):
    workspace = workspace or {}
    var = _sym(var_name)
    local_ws = dict(workspace)
    local_ws[var_name] = var
    expr = safe_parse(expr_str, local_ws)

    # 有上下限 -> 定积分；否则不定积分
    if a is not None and b is not None and str(a).strip() != "" and str(b).strip() != "":
        a_expr = safe_parse(str(a), local_ws)
        b_expr = safe_parse(str(b), local_ws)
        res = sp.integrate(expr, (var, a_expr, b_expr))
    else:
        res = sp.integrate(expr, var)

    res_s = sp.simplify(res)
    return {
        "kind": "text",
        "expr_latex": sp.latex(expr),
        "result_str": str(res_s),
        "result_latex": sp.latex(res_s),
    }

def solve_expr(eq_str: str, var_name="x", method="symbolic", x0=None, workspace: dict | None = None):
    workspace = workspace or {}
    var = _sym(var_name)
    eq = parse_equation(eq_str, var, workspace)

    method = (method or "symbolic").lower()

    if method == "numeric":
        if x0 is None or str(x0).strip() == "":
            raise ValueError("数值解需要初值 x0")
        x0_expr = safe_parse(str(x0), {var_name: var, **workspace, **ALLOWED})
        sol = sp.nsolve(eq, var, x0_expr)
        solN = sp.N(sol)
        return {
            "kind": "text",
            "expr_latex": sp.latex(eq),
            "result_str": str(solN),
            "result_latex": sp.latex(solN),
        }

    # symbolic
    sols = sp.solve(eq, var)
    # 可能返回列表/集合/表达式
    if isinstance(sols, (list, tuple, set)):
        sols_list = list(sols)
        result_str = "[" + ", ".join(map(str, sols_list)) + "]"
        result_latex = r"\left[" + ", ".join(sp.latex(s) for s in sols_list) + r"\right]"
    else:
        result_str = str(sols)
        result_latex = sp.latex(sols)

    return {
        "kind": "text",
        "expr_latex": sp.latex(eq),
        "result_str": result_str,
        "result_latex": result_latex,
    }

def plot_2d(func_str: str, var_name="x", x_min=-5, x_max=5, n=400, workspace: dict | None = None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    workspace = workspace or {}
    var = _sym(var_name)
    local_ws = dict(workspace)
    local_ws[var_name] = var

    f_expr = safe_parse(func_str, local_ws)
    f = sp.lambdify(var, f_expr, modules=["numpy"])

    x_min = float(x_min)
    x_max = float(x_max)
    n = int(n)
    if n < 50 or n > 5000:
        raise ValueError("点数建议 50~5000")

    xs = np.linspace(x_min, x_max, n)
    ys = f(xs)
    
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ys = f(xs)

    ys = np.array(ys, dtype=float)

    # ✅ 1) 非有限值断开
    ys[~np.isfinite(ys)] = np.nan

    # ✅ 2) 裁剪过大的值（避免竖线/拉爆 y 轴）
    abs_y = np.abs(ys)
    finite_abs = abs_y[np.isfinite(abs_y)]
    if finite_abs.size > 0:
        cap = np.nanpercentile(finite_abs, 98)  # 98分位当作“合理上界”
        cap = max(cap * 3, 50)                  # 给一点余量，且不低于50
        ys[abs_y > cap] = np.nan
    finite_y = ys[np.isfinite(ys)]
    
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(xs, ys)
    ax.grid(True, alpha=0.25)
    ax.set_xlabel(var_name)
    ax.set_ylabel(f"f({var_name})")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
    return {
        "kind": "plot",
        "func_latex": sp.latex(f_expr),
        "img_base64": img_b64,
    }

def run(mode: str, payload: dict, workspace: dict | None = None):
    workspace = workspace or {}
    mode = (mode or "eval").lower()

    expr = payload.get("expr", "")
    var = payload.get("var", "x")
    order = payload.get("order", 1)
    a = payload.get("a", None)
    b = payload.get("b", None)
    method = payload.get("method", "symbolic")
    x0 = payload.get("x0", None)

    if mode == "eval":
        return eval_expr(expr, workspace)
    if mode == "simplify":
        return simplify_expr(expr, workspace)
    if mode == "diff":
        return diff_expr(expr, var, order, workspace)
    if mode == "integrate":
        return integrate_expr(expr, var, a, b, workspace)
    if mode == "solve":
        return solve_expr(expr, var, method, x0, workspace)
    if mode == "plot":
        return plot_2d(
            func_str=expr,
            var_name=var,
            x_min=payload.get("x_min", -10),
            x_max=payload.get("x_max", 10),
            n=payload.get("n", 400),
            workspace=workspace
        )

    raise ValueError(f"不支持的模式：{mode}")