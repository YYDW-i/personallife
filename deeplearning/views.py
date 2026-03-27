from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .forms import DATASET_CHOICES, DEFAULT_FORM_DATA, DeepLearningBuilderForm
from .utils.code_generator import generate_pytorch_code
from .utils.trainer import get_training_job, start_training_job

DATASET_TASK_MAP = {
    "normal_regression": "regression",
    "normal_classification": "classification",
    "iris": "classification",
    "breast_cancer": "classification",
    "digits": "classification",
    "mnist": "classification",
    "fashion_mnist": "classification",
}


def _normalize_config(raw_data: dict) -> dict:
    config = dict(raw_data)

    dataset_name = config.get("dataset_name", "normal_regression")
    config["task_type"] = DATASET_TASK_MAP.get(dataset_name, "regression")

    hidden_sizes = config.get("hidden_sizes", "")
    if isinstance(hidden_sizes, str):
        hidden_list = [int(x.strip()) for x in hidden_sizes.split(",") if x.strip()]
    else:
        hidden_list = hidden_sizes

    config["hidden_sizes_list"] = hidden_list
    config["normalize_data"] = bool(config.get("normalize_data", False))
    config["custom_formula"] = (config.get("custom_formula", "") or "").strip() or "x @ w + b"
    return config


@require_GET
def builder(request):
    form = DeepLearningBuilderForm(initial=DEFAULT_FORM_DATA)
    config = _normalize_config(DEFAULT_FORM_DATA)
    generated_code = generate_pytorch_code(config)

    context = {
        "form": form,
        "generated_code": generated_code,
    }
    return render(request, "deeplearning/builder.html", context)


@require_POST
def generate_code_api(request):
    form = DeepLearningBuilderForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {
                "ok": False,
                "errors": form.errors.get_json_data(),
            },
            status=400,
        )

    config = _normalize_config(form.cleaned_data)
    code = generate_pytorch_code(config)
    return JsonResponse(
        {
            "ok": True,
            "code": code,
            "task_type": config["task_type"],
        }
    )


@require_POST
def start_training_api(request):
    form = DeepLearningBuilderForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {
                "ok": False,
                "errors": form.errors.get_json_data(),
            },
            status=400,
        )

    config = _normalize_config(form.cleaned_data)

    job_id = start_training_job(config)

    return JsonResponse(
        {
            "ok": True,
            "job_id": job_id,
            "message": "训练任务已启动。",
            "total_epochs": int(config["epochs"]),
        }
    )


@require_GET
def training_status_api(request, job_id):
    job = get_training_job(job_id)
    if not job:
        return JsonResponse(
            {
                "ok": False,
                "message": "找不到该训练任务。",
            },
            status=404,
        )

    return JsonResponse(
        {
            "ok": True,
            "job": job,
        }
    )