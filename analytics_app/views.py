from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .iching_core import cast_hexagram, render_lines
from .iching_data import ensure_dataset_ready, get_hex_by_array
from .zhipu_client import zhipu_interpret_optional

from django.http import JsonResponse
from django.core import signing
from django.template.loader import render_to_string


def _ai_context(request, question, primary, moving_lines):
    return signing.dumps({"user": request.user.pk, "question": question,
                          "array": primary["array"], "moving_lines": moving_lines},
                         salt="iching-ai", compress=True)


def _ai_html(request, ai, token):
    return render_to_string("analytics_app/iching/_ai_result.html",
                            {"ai": ai, "ai_token": token, "can_retry": True}, request=request)


@login_required
@require_http_methods(["POST"])
def iching_interpret(request):
    try:
        token = request.POST.get("token", "")
        if len(token) > 16000:
            raise signing.BadSignature
        context = signing.loads(token, salt="iching-ai", max_age=3600)
        if context["user"] != request.user.pk:
            raise signing.BadSignature
    except (signing.BadSignature, KeyError, TypeError):
        return JsonResponse({"error": "卦象凭证已过期或无效，请重新起卦。"}, status=400)
    primary = get_hex_by_array(context["array"])
    moving = context["moving_lines"]
    relating_array = [1 - bit if i in moving else bit for i, bit in enumerate(primary["array"], 1)]
    relating = get_hex_by_array(relating_array) if moving else None
    ai = zhipu_interpret_optional(context["question"], primary, relating, moving)
    return JsonResponse({"ai": ai, "html": _ai_html(request, ai, token)})

@login_required
@require_http_methods(["GET"])
def index(request):
    return redirect("analytics_app:iching_index")

@login_required
@require_http_methods(["GET"])
def iching_index(request):
    return render(request, "analytics_app/iching/index.html")


@login_required
@require_http_methods(["POST"])
def iching_cast(request):
    question = (request.POST.get("question") or "").strip()
    if len(question) > 1000:
        return JsonResponse({"error": "问题请控制在 1000 字以内。"}, status=400)
    method = request.POST.get("method") or "coins"
    if method not in ("coins", "random", "time"):
        return JsonResponse({"error": "不支持的起卦方式"}, status=400)
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
        "coin_results": r.coin_results,
        "ai_token": _ai_context(request, question, primary, r.moving_lines),
    }
    return render(request, "analytics_app/iching/result.html", ctx)

@login_required
@require_http_methods(["POST"])
def iching_cast_ajax(request):
    question = (request.POST.get("question") or "").strip()
    if len(question) > 1000:
        return JsonResponse({"error": "问题请控制在 1000 字以内。"}, status=400)
    method = request.POST.get("method") or "coins"
    if method not in ("coins", "random", "time"):
        return JsonResponse({"error": "不支持的起卦方式"}, status=400)
    use_ai = request.POST.get("use_ai") == "1"

    try:
        ensure_dataset_ready()
    except Exception as e:
        return JsonResponse({"error": f"卦象数据未就绪：{e}"}, status=500)

    r = cast_hexagram(method=method)
    primary = get_hex_by_array(r.primary_arr)
    relating = get_hex_by_array(r.relating_arr) if r.relating_arr else None
    primary_lines = list(reversed(render_lines(primary["array"], r.moving_lines, r.line_nums)))
    relating_lines = list(reversed(render_lines(relating["array"], [], r.line_nums))) if relating else None

    ai = None
    if use_ai:
        ai = zhipu_interpret_optional(
            question=question,
            primary=primary,
            relating=relating,
            moving_lines=r.moving_lines
        )

    token = _ai_context(request, question, primary, r.moving_lines)
    data = {
        "question": question,
        "method": method,
        "primary": primary,
        "relating": relating,
        "moving_lines": r.moving_lines,
        "line_nums": r.line_nums,
        "primary_lines": primary_lines,
        "relating_lines": relating_lines,
        "ai": ai,
        "coin_results": r.coin_results,
        "ai_token": token,
        "ai_html": _ai_html(request, ai, token) if ai else "",
    }
    
    return JsonResponse(data)
