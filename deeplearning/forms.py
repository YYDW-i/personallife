from django import forms


class DeepLearningConfigForm(forms.Form):
    DATASET_SOURCE_CHOICES = [
        ("builtin", "内置公开数据集"),
        ("synthetic", "随机生成数据集"),
    ]

    BUILTIN_DATASET_CHOICES = [
        ("mnist", "MNIST 手写数字"),
        ("fashion_mnist", "FashionMNIST 服饰分类"),
        ("cifar10", "CIFAR10 彩色图像分类"),
    ]

    SYNTHETIC_TASK_CHOICES = [
        ("normal_regression", "正态分布回归数据"),
        ("normal_classification", "正态分布二分类数据"),
    ]

    MODEL_TYPE_CHOICES = [
        ("linear_model", "线性模型（如 y = Wx + b）"),
        ("mlp", "多层感知机 MLP"),
        ("custom_formula", "自定义公式（先只生成代码，不直接执行）"),
    ]

    ACTIVATION_CHOICES = [
        ("relu", "ReLU"),
        ("sigmoid", "Sigmoid"),
        ("tanh", "Tanh"),
        ("leaky_relu", "LeakyReLU"),
    ]

    OPTIMIZER_CHOICES = [
        ("sgd", "SGD"),
        ("adam", "Adam"),
        ("adagrad", "Adagrad"),
        ("rmsprop", "RMSprop"),
    ]

    LOSS_CHOICES = [
        ("auto", "自动匹配（推荐）"),
        ("mse", "MSELoss"),
        ("cross_entropy", "CrossEntropyLoss"),
    ]

    dataset_source = forms.ChoiceField(
        label="数据集来源",
        choices=DATASET_SOURCE_CHOICES,
        initial="synthetic",
    )
    builtin_dataset = forms.ChoiceField(
        label="内置数据集",
        choices=BUILTIN_DATASET_CHOICES,
        required=False,
        initial="mnist",
    )
    synthetic_task = forms.ChoiceField(
        label="随机数据类型",
        choices=SYNTHETIC_TASK_CHOICES,
        required=False,
        initial="normal_regression",
    )
    n_samples = forms.IntegerField(label="样本数", min_value=50, max_value=50000, initial=500)
    input_dim = forms.IntegerField(label="输入维度", min_value=1, max_value=128, initial=1)
    noise_std = forms.FloatField(label="噪声标准差", min_value=0.0, max_value=10.0, initial=0.1)

    model_type = forms.ChoiceField(label="模型类型", choices=MODEL_TYPE_CHOICES, initial="linear_model")
    custom_formula = forms.CharField(
        label="自定义公式",
        required=False,
        initial="y = w * x + b",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="这部分目前只用于生成示意代码，不在服务器端直接执行。",
    )
    hidden_layers = forms.CharField(
        label="隐藏层结构",
        required=False,
        initial="64,32",
        help_text="仅 MLP 使用，示例：64,32",
    )
    activation = forms.ChoiceField(label="激活函数", choices=ACTIVATION_CHOICES, initial="relu")
    dropout = forms.FloatField(label="Dropout", min_value=0.0, max_value=0.9, initial=0.0)

    optimizer = forms.ChoiceField(label="优化器", choices=OPTIMIZER_CHOICES, initial="adam")
    loss_function = forms.ChoiceField(label="损失函数", choices=LOSS_CHOICES, initial="auto")
    learning_rate = forms.FloatField(label="学习率", min_value=0.00001, max_value=1.0, initial=0.01)
    batch_size = forms.IntegerField(label="Batch Size", min_value=1, max_value=4096, initial=32)
    epochs = forms.IntegerField(label="训练轮数 Epochs", min_value=1, max_value=1000, initial=30)
    run_demo = forms.BooleanField(label="在页面中直接跑一个演示训练", required=False, initial=True)

    def clean_hidden_layers(self):
        raw = self.cleaned_data.get("hidden_layers", "")
        if not raw.strip():
            return "64,32"
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if not all(p.isdigit() and int(p) > 0 for p in parts):
            raise forms.ValidationError("隐藏层请写成 64,32 这样的正整数逗号分隔格式。")
        return ",".join(parts)

    def clean(self):
        cleaned = super().clean()
        dataset_source = cleaned.get("dataset_source")
        model_type = cleaned.get("model_type")
        loss_function = cleaned.get("loss_function")
        synthetic_task = cleaned.get("synthetic_task")

        if dataset_source == "builtin" and not cleaned.get("builtin_dataset"):
            self.add_error("builtin_dataset", "请选择一个内置数据集。")

        if dataset_source == "synthetic" and not synthetic_task:
            self.add_error("synthetic_task", "请选择一个随机数据任务。")

        task = "classification" if dataset_source == "builtin" or synthetic_task == "normal_classification" else "regression"

        if loss_function == "mse" and task == "classification":
            self.add_error("loss_function", "分类任务不建议使用 MSELoss。")
        if loss_function == "cross_entropy" and task == "regression":
            self.add_error("loss_function", "回归任务不建议使用 CrossEntropyLoss。")

        if model_type == "custom_formula" and cleaned.get("run_demo"):
            cleaned["run_demo"] = False

        return cleaned
