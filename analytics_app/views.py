from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .iching_core import cast_hexagram, render_lines
from .iching_data import ensure_dataset_ready, get_hex_by_array
from .zhipu_client import zhipu_interpret_optional

@login_required
@require_http_methods(["GET"])
def index(request):
    return render(request, "analytics_app/index.html")

@require_http_methods(["GET"])
def iching_index(request):
    return render(request, "analytics_app/iching/index.html")


@require_http_methods(["POST"])
def iching_cast(request):
    question = (request.POST.get("question") or "").strip()
    method = request.POST.get("method") or "coins"
    use_ai = request.POST.get("use_ai") == "1"
    
    try:
        # 确保本地 iching.json 存在：没有就自动下载一次并缓存
        ensure_dataset_ready()
    except Exception as e:
        messages.error(
            request,
            f"卦象数据未就绪：{e}。请先运行：python manage.py iching_seed"
        )
        return redirect("analytics_app:iching_index")

    # 起卦
    r = cast_hexagram(method=method)

    # 查卦（本卦/之卦）
    primary = get_hex_by_array(r.primary_arr)
    relating = get_hex_by_array(r.relating_arr) if r.relating_arr else None

    # 画六爻（顶部在上，所以要 reversed）
    primary_lines = list(reversed(render_lines(primary["array"], r.moving_lines, r.line_nums)))
    relating_lines = list(reversed(render_lines(relating["array"], [], r.line_nums))) if relating else None

    # AI：生成译文/建议/典故（可选）
    ai = None
    if use_ai:
        ai = zhipu_interpret_optional(
            question=question,
            primary=primary,
            relating=relating,
            moving_lines=r.moving_lines
        )
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"AI 返回内容: {ai}")
        # 也可以直接打印到控制台（开发服务器会显示）
        print("=== AI DEBUG ===")
        print(ai)

    ctx = {
        "question": question,
        "method": method,
        "primary": primary,
        "relating": relating,
        "moving_lines": r.moving_lines,
        "line_nums": r.line_nums,
        "primary_lines": primary_lines,
        "relating_lines": relating_lines,
        "ai": ai,
    }
    return render(request, "analytics_app/iching/result.html", ctx)
