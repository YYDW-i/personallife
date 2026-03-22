from django.shortcuts import render

from .forms import DeepLearningConfigForm
from .utils.code_generator import generate_pytorch_code
from .utils.trainer import train_demo



def builder(request):
    generated_code = None
    plot_base64 = None
    training_summary = None

    if request.method == "POST":
        form = DeepLearningConfigForm(request.POST)
        if form.is_valid():
            config = form.cleaned_data
            generated_code = generate_pytorch_code(config)

            if config.get("run_demo"):
                plot_base64, training_summary = train_demo(config)
            else:
                training_summary = {
                    "message": "当前没有执行演示训练。你可以直接复制右侧生成的 PyTorch 代码到本地运行。"
                }
    else:
        form = DeepLearningConfigForm()

    context = {
        "form": form,
        "generated_code": generated_code,
        "plot_base64": plot_base64,
        "training_summary": training_summary,
    }
    return render(request, "deeplearning/builder.html", context)
