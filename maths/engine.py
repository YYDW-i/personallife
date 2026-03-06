import base64
import io
import re
import numpy as np
import sympy as sp

import ast

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

def plot_3d(func_str: str,
            x_name="x", y_name="y",
            x_min=-5, x_max=5,
            y_min=-5, y_max=5,
            n=80,
            workspace: dict | None = None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    workspace = workspace or {}
    x = _sym(x_name)
    y = _sym(y_name)

    local_ws = dict(workspace)
    local_ws[x_name] = x
    local_ws[y_name] = y

    expr = safe_parse(func_str, local_ws)
    f = sp.lambdify((x, y), expr, modules=["numpy"])

    x_min = float(x_min); x_max = float(x_max)
    y_min = float(y_min); y_max = float(y_max)
    n = int(n)
    if n < 20 or n > 250:
        raise ValueError("3D 网格点数 n 建议 20~250（太大很卡）")

    xs = np.linspace(x_min, x_max, n)
    ys = np.linspace(y_min, y_max, n)
    X, Y = np.meshgrid(xs, ys)

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        Z = f(X, Y)

    Z = np.array(Z, dtype=float)

    # 1) 非有限值断开（不连续/除零）
    Z[~np.isfinite(Z)] = np.nan

    # 2) 裁剪爆炸值（避免“冲天柱”把图拉爆）
    abs_z = np.abs(Z)
    finite_abs = abs_z[np.isfinite(abs_z)]
    if finite_abs.size > 0:
        cap = np.nanpercentile(finite_abs, 98)
        cap = max(cap * 3, 50)
        Z[abs_z > cap] = np.nan

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(X, Y, Z, rstride=1, cstride=1, linewidth=0, antialiased=True)

    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.set_zlabel("z")

    # 可选：加一个俯视投影等高线，更好读（你喜欢可以保留）
    # ax.contour(X, Y, Z, zdir='z', offset=np.nanmin(Z[np.isfinite(Z)]) if np.isfinite(Z).any() else -1, linewidths=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
    return {
        "kind": "plot",
        "func_latex": sp.latex(expr),
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
    if mode == "plot3d":
        return plot_3d(
            func_str=expr,
            x_name=payload.get("x_var", "x"),
            y_name=payload.get("y_var", "y"),
            x_min=payload.get("x_min", -5),
            x_max=payload.get("x_max", 5),
            y_min=payload.get("y_min", -5),
            y_max=payload.get("y_max", 5),
            n=payload.get("n", 80),
            workspace=workspace
        )
    if mode == "limit":
        return limit_expr(expr, var, payload.get("approach", "0"), payload.get("direction", "+-"), workspace)
    if mode == "series":
        order = payload.get("order")
        # 如果 order 不存在或为空字符串，则使用默认值 6
        if order is None or order == "":
            order = 6
        return series_expr(expr, var, payload.get("point", "0"), order, workspace)
    if mode == "ml":
        ml_op = payload.get("ml_op", "gradient")
        vars_str = payload.get("vars", "x")
        if ml_op == "gradient":
            return gradient(expr, vars_str, workspace)
        elif ml_op == "jacobian":
            # expr 此时应包含多个函数表达式，用分号分隔
            return jacobian(expr, vars_str, workspace)
        elif ml_op == "hessian":
            return hessian(expr, vars_str, workspace)
        elif ml_op == "gd_demo":
            x0 = payload.get("x0", "0,0")
            lr = float(payload.get("lr", 0.1))
            steps = int(payload.get("steps", 20))
            return gradient_descent_demo(expr, vars_str, x0, lr, steps)
        else:
            raise ValueError(f"不支持的 ML 子操作: {ml_op}")
    raise ValueError(f"不支持的模式：{mode}")

def _parse_matrix(mat_str):
    """将字符串如 '[[1,2],[3,4]]' 转换为嵌套列表，支持符号"""
    try:
        # 尝试使用 ast.literal_eval 安全解析
        mat = ast.literal_eval(mat_str)
        if isinstance(mat, list) and all(isinstance(row, list) for row in mat):
            return mat
        else:
            raise ValueError("矩阵格式应为二维列表，例如 [[1,2],[3,4]]")
    except:
        raise ValueError("矩阵格式不正确")

def linear_algebra(op: str, matrix_a: str, matrix_b: str = None, vector: str = None, workspace: dict = None):
    """
    支持的操作：
        det: 行列式
        inv: 逆矩阵
        eig: 特征值和特征向量
        solve: 解线性方程组 Ax = b (b 为向量或矩阵)
        rank: 矩阵的秩
        transpose: 转置
    """
    workspace = workspace or {}
    A_list = _parse_matrix(matrix_a)
    # 将列表转换为 numpy 数组（数值计算）
    try:
        A = np.array(A_list, dtype=float)
    except:
        raise ValueError("矩阵元素必须为数值")

    if op == "det":
        if A.shape[0] != A.shape[1]:
            raise ValueError("行列式只对方阵定义")
        result = np.linalg.det(A)
        result_latex = sp.latex(result)
        result_str = str(result)
    elif op == "inv":
        if A.shape[0] != A.shape[1]:
            raise ValueError("逆矩阵只对方阵定义")
        inv = np.linalg.inv(A)
        result_str = str(inv.tolist())
        result_latex = sp.latex(sp.Matrix(inv))  # 转换为 sympy 矩阵以获得 LaTeX
    elif op == "eig":
        eigvals, eigvecs = np.linalg.eig(A)
        # 将结果转换为可读格式
        result_str = f"特征值: {eigvals}\n特征向量:\n{eigvecs}"
        # 生成 LaTeX 表示（简化）
        result_latex = sp.latex(sp.Matrix(eigvals)) + r"\\" + sp.latex(sp.Matrix(eigvecs))
    elif op == "solve":
        if not matrix_b and not vector:
            raise ValueError("解方程需要提供 b (矩阵或向量)")
        if vector:
            b = np.array(_parse_matrix(vector), dtype=float).flatten()
        else:
            b = np.array(_parse_matrix(matrix_b), dtype=float)
        x = np.linalg.solve(A, b)
        result_str = str(x.tolist())
        result_latex = sp.latex(sp.Matrix(x))
    elif op == "rank":
        rank = np.linalg.matrix_rank(A)
        result_str = str(rank)
        result_latex = str(rank)
    elif op == "transpose":
        T = A.T
        result_str = str(T.tolist())
        result_latex = sp.latex(sp.Matrix(T))
    else:
        raise ValueError(f"不支持的线性代数操作: {op}")

    return {
        "kind": "text",
        "result_str": result_str,
        "result_latex": result_latex,
    }

def limit_expr(expr_str: str, var_name="x", approach="0", direction="+-", workspace: dict = None):
    workspace = workspace or {}
    var = _sym(var_name)
    local_ws = dict(workspace)
    local_ws[var_name] = var
    expr = safe_parse(expr_str, local_ws)
    approach_val = safe_parse(approach, local_ws)
    # direction: '+' 右极限, '-' 左极限, '+-' 双边极限
    if direction == "+":
        limit = sp.limit(expr, var, approach_val, dir="+")
    elif direction == "-":
        limit = sp.limit(expr, var, approach_val, dir="-")
    else:
        limit = sp.limit(expr, var, approach_val)
    return {
        "kind": "text",
        "expr_latex": sp.latex(expr),
        "result_str": str(limit),
        "result_latex": sp.latex(limit),
    }

def series_expr(expr_str: str, var_name="x", point="0", order=6, workspace: dict | None = None):
    workspace = workspace or {}
    var = _sym(var_name)
    local_ws = dict(workspace)
    local_ws[var_name] = var
    expr = safe_parse(expr_str, local_ws)
    point_val = safe_parse(point, local_ws)

    # 确保 order 是正整数
    try:
        order = int(order)
        if order <= 0:
            raise ValueError("展开阶数必须为正整数")
    except ValueError:
        raise ValueError("展开阶数必须为整数")

    series = sp.series(expr, var, point_val, order)
    return {
        "kind": "text",
        "expr_latex": sp.latex(expr),
        "result_str": str(series),
        "result_latex": sp.latex(series),
    }


# ---------- 机器学习专用工具 ----------

def gradient(expr_str: str, vars_str: str, workspace: dict = None):
    """
    计算多元标量函数的梯度向量
    :param expr_str: 表达式，例如 "x**2 + y**2"
    :param vars_str: 变量列表，逗号分隔，例如 "x, y"
    :param workspace: 工作空间
    :return: 包含梯度向量字符串和 LaTeX 的字典
    """
    workspace = workspace or {}
    # 解析变量列表
    var_names = [v.strip() for v in vars_str.split(',') if v.strip()]
    if not var_names:
        raise ValueError("至少需要提供一个变量")
    symbols = [_sym(name) for name in var_names]
    local_ws = dict(workspace)
    for name, sym in zip(var_names, symbols):
        local_ws[name] = sym

    expr = safe_parse(expr_str, local_ws)
    # 计算梯度：对每个变量求偏导
    grad = [sp.diff(expr, sym) for sym in symbols]
    grad_simplified = [sp.simplify(g) for g in grad]

    # 格式化输出
    grad_str = "[" + ", ".join(str(g) for g in grad_simplified) + "]"
    grad_latex = r"\nabla f = \begin{bmatrix}" + \
                 r" \\ ".join(sp.latex(g) for g in grad_simplified) + \
                 r"\end{bmatrix}"
    return {
        "kind": "text",
        "expr_latex": sp.latex(expr),
        "result_str": grad_str,
        "result_latex": grad_latex,
    }

def jacobian(exprs_str: str, vars_str: str, workspace: dict = None):
    """
    计算多个函数关于变量的雅可比矩阵
    :param exprs_str: 函数列表，用分号分隔，例如 "x*y; x**2 + y**2"
    :param vars_str: 变量列表，逗号分隔
    """
    workspace = workspace or {}
    var_names = [v.strip() for v in vars_str.split(',') if v.strip()]
    if not var_names:
        raise ValueError("至少需要提供一个变量")
    symbols = [_sym(name) for name in var_names]
    local_ws = dict(workspace)
    for name, sym in zip(var_names, symbols):
        local_ws[name] = sym

    # 解析多个表达式
    expr_strings = [e.strip() for e in exprs_str.split(';') if e.strip()]
    if not expr_strings:
        raise ValueError("至少需要提供一个函数")

    exprs = [safe_parse(e, local_ws) for e in expr_strings]

    # 构建雅可比矩阵：行对应函数，列对应变量
    J = []
    for f in exprs:
        row = [sp.diff(f, sym) for sym in symbols]
        J.append(row)

    # 简化每个元素
    J_simple = [[sp.simplify(entry) for entry in row] for row in J]

    # 格式化输出
    J_latex = r"\mathbf{J} = \begin{bmatrix}"
    for i, row in enumerate(J_simple):
        row_latex = " & ".join(sp.latex(entry) for entry in row)
        J_latex += row_latex
        if i < len(J_simple)-1:
            J_latex += r" \\ "
    J_latex += r"\end{bmatrix}"

    # 字符串表示（简化）
    J_str = "\n".join([str(row) for row in J_simple])

    return {
        "kind": "text",
        "result_str": J_str,
        "result_latex": J_latex,
    }

def hessian(expr_str: str, vars_str: str, workspace: dict = None):
    """
    计算标量函数的海森矩阵
    """
    workspace = workspace or {}
    var_names = [v.strip() for v in vars_str.split(',') if v.strip()]
    if not var_names:
        raise ValueError("至少需要提供一个变量")
    symbols = [_sym(name) for name in var_names]
    local_ws = dict(workspace)
    for name, sym in zip(var_names, symbols):
        local_ws[name] = sym

    expr = safe_parse(expr_str, local_ws)

    # 计算海森矩阵
    H = sp.hessian(expr, symbols)
    # 简化每个元素
    H_simple = sp.simplify(H)

    # 格式化输出
    H_latex = sp.latex(H_simple)
    H_str = str(H_simple)

    return {
        "kind": "text",
        "expr_latex": sp.latex(expr),
        "result_str": H_str,
        "result_latex": H_latex,
    }

def gradient_descent_demo(func_str: str, vars_str: str, x0_str: str, lr: float = 0.1, steps: int = 20):
    """
    梯度下降数值演示，绘制函数等高线和迭代轨迹
    :param func_str: 二元函数表达式，例如 "x**2 + y**2"
    :param vars_str: 变量名，例如 "x, y"
    :param x0_str: 初始点，例如 "1, 2"
    :param lr: 学习率
    :param steps: 迭代步数
    :return: 包含图像 base64 的字典
    """
    import matplotlib.pyplot as plt
    from matplotlib import cm
    import numpy as np

    # 解析变量和初始点
    var_names = [v.strip() for v in vars_str.split(',') if v.strip()]
    if len(var_names) != 2:
        raise ValueError("梯度下降演示目前只支持二元函数")
    x_name, y_name = var_names[0], var_names[1]
    x_sym = _sym(x_name)
    y_sym = _sym(y_name)

    # 解析初始点
    x0_vals = [float(v.strip()) for v in x0_str.split(',') if v.strip()]
    if len(x0_vals) != 2:
        raise ValueError("初始点需要两个数值，例如 '1, 2'")

    # 解析函数表达式
    expr = safe_parse(func_str, {x_name: x_sym, y_name: y_sym})

    # 计算梯度函数
    grad_x = sp.lambdify((x_sym, y_sym), sp.diff(expr, x_sym), modules='numpy')
    grad_y = sp.lambdify((x_sym, y_sym), sp.diff(expr, y_sym), modules='numpy')
    f = sp.lambdify((x_sym, y_sym), expr, modules='numpy')

    # 执行梯度下降
    points = [np.array(x0_vals, dtype=float)]
    for _ in range(steps):
        x, y = points[-1]
        gx = grad_x(x, y)
        gy = grad_y(x, y)
        new_x = x - lr * gx
        new_y = y - lr * gy
        points.append(np.array([new_x, new_y]))
    points = np.array(points)

    # 绘制等高线和轨迹
    x_min, x_max = min(points[:,0].min(), -2), max(points[:,0].max(), 2)
    y_min, y_max = min(points[:,1].min(), -2), max(points[:,1].max(), 2)
    X, Y = np.meshgrid(np.linspace(x_min, x_max, 100),
                       np.linspace(y_min, y_max, 100))
    Z = f(X, Y)

    fig, ax = plt.subplots(figsize=(8,6))
    contour = ax.contour(X, Y, Z, levels=20, cmap=cm.viridis)
    ax.clabel(contour, inline=True, fontsize=8)
    ax.plot(points[:,0], points[:,1], 'ro-', markersize=4, label='GD path')
    ax.plot(points[0,0], points[0,1], 'go', markersize=8, label='Start')
    ax.plot(points[-1,0], points[-1,1], 'bo', markersize=8, label='End')
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.set_title(f"Gradient Descent, lr={lr}, steps={steps}")
    ax.legend()
    ax.grid(alpha=0.3)

    # 保存为 base64
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')

    return {
        "kind": "plot",
        "img_base64": img_b64,
        "func_latex": sp.latex(expr),
    }