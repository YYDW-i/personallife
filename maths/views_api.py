import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .engine import eval_expr, plot_2d

@login_required
@require_POST
def api_eval(request):
    payload = json.loads(request.body.decode("utf-8"))
    expr = payload.get("expr", "")
    # MVP 先不做 workspace，后面再加
    try:
        out = eval_expr(expr, workspace={})
        return JsonResponse({"ok": True, "data": out})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

@login_required
@require_POST
def api_plot(request):
    payload = json.loads(request.body.decode("utf-8"))
    func = payload.get("func", "")
    x_min = payload.get("x_min", -5)
    x_max = payload.get("x_max", 5)
    try:
        n = payload.get("n", 400)
        out = plot_2d(func, "x", x_min, x_max, n=n)
        return JsonResponse({"ok": True, "data": out})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)