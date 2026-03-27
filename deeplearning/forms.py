from django import forms

DATASET_CHOICES = [
    ("normal_regression", "随机正态分布回归"),
    ("normal_classification", "随机正态分布分类"),
    ("iris", "Iris 鸢尾花分类"),
    ("breast_cancer", "Breast Cancer 乳腺癌分类"),
    ("digits", "Digits 手写数字分类（8x8）"),
    ("mnist", "MNIST 手写数字（在线下载）"),
    ("fashion_mnist", "FashionMNIST 服饰分类（在线下载）"),
]

MODEL_CHOICES = [
    ("linear", "线性模型"),
    ("mlp", "多层感知机 MLP"),
    ("custom_formula", "自定义公式"),
]

ACTIVATION_CHOICES = [
    ("relu", "ReLU"),
    ("tanh", "Tanh"),
    ("sigmoid", "Sigmoid"),
    ("leaky_relu", "LeakyReLU"),
    ("none", "None"),
]

OPTIMIZER_CHOICES = [
    ("sgd", "SGD"),
    ("adam", "Adam"),
    ("adamw", "AdamW"),
    ("rmsprop", "RMSprop"),
]

DEFAULT_FORM_DATA = {
    "dataset_name": "normal_regression",
    "num_samples": 800,
    "input_dim": 1,
    "noise_std": 0.2,
    "num_classes": 2,
    "test_size": 0.2,
    "random_seed": 42,
    "normalize_data": True,
    "model_name": "linear",
    "custom_formula": "y = w*x + b",
    "hidden_sizes": "64,32",
    "activation": "relu",
    "dropout": 0.0,
    "optimizer": "adam",
    "learning_rate": 0.01,
    "batch_size": 32,
    "epochs": 30,
}


class DeepLearningBuilderForm(forms.Form):
    dataset_name = forms.ChoiceField(
        label="数据集",
        choices=DATASET_CHOICES,
        initial=DEFAULT_FORM_DATA["dataset_name"],
    )
    num_samples = forms.IntegerField(
        label="样本数",
        min_value=100,
        max_value=50000,
        initial=DEFAULT_FORM_DATA["num_samples"],
    )
    input_dim = forms.IntegerField(
        label="输入维度",
        min_value=1,
        max_value=2048,
        initial=DEFAULT_FORM_DATA["input_dim"],
    )
    noise_std = forms.FloatField(
        label="噪声强度",
        min_value=0.0,
        max_value=10.0,
        initial=DEFAULT_FORM_DATA["noise_std"],
    )
    num_classes = forms.IntegerField(
        label="类别数（仅随机分类）",
        min_value=2,
        max_value=20,
        initial=DEFAULT_FORM_DATA["num_classes"],
    )
    test_size = forms.FloatField(
        label="测试集比例",
        min_value=0.1,
        max_value=0.5,
        initial=DEFAULT_FORM_DATA["test_size"],
    )
    random_seed = forms.IntegerField(
        label="随机种子",
        min_value=0,
        max_value=999999,
        initial=DEFAULT_FORM_DATA["random_seed"],
    )
    normalize_data = forms.BooleanField(
        label="标准化输入数据",
        required=False,
        initial=DEFAULT_FORM_DATA["normalize_data"],
    )

    model_name = forms.ChoiceField(
        label="模型",
        choices=MODEL_CHOICES,
        initial=DEFAULT_FORM_DATA["model_name"],
    )
    custom_formula = forms.CharField(
        label="自定义公式",
        required=False,
        initial=DEFAULT_FORM_DATA["custom_formula"],
    )
    hidden_sizes = forms.CharField(
        label="隐藏层",
        required=False,
        initial=DEFAULT_FORM_DATA["hidden_sizes"],
        help_text="例如：64,32,16",
    )
    activation = forms.ChoiceField(
        label="激活函数",
        choices=ACTIVATION_CHOICES,
        initial=DEFAULT_FORM_DATA["activation"],
    )
    dropout = forms.FloatField(
        label="Dropout",
        min_value=0.0,
        max_value=0.9,
        initial=DEFAULT_FORM_DATA["dropout"],
    )
    optimizer = forms.ChoiceField(
        label="优化器",
        choices=OPTIMIZER_CHOICES,
        initial=DEFAULT_FORM_DATA["optimizer"],
    )
    learning_rate = forms.FloatField(
        label="学习率",
        min_value=1e-6,
        max_value=10.0,
        initial=DEFAULT_FORM_DATA["learning_rate"],
    )
    batch_size = forms.IntegerField(
        label="Batch Size",
        min_value=1,
        max_value=4096,
        initial=DEFAULT_FORM_DATA["batch_size"],
    )
    epochs = forms.IntegerField(
        label="Epochs",
        min_value=1,
        max_value=500,
        initial=DEFAULT_FORM_DATA["epochs"],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "dl-checkbox"})
            else:
                field.widget.attrs.update({"class": "dl-input"})

    def clean_hidden_sizes(self):
        value = self.cleaned_data.get("hidden_sizes", "").strip()
        if not value:
            return ""
        try:
            parsed = [int(x.strip()) for x in value.split(",") if x.strip()]
            if any(x <= 0 for x in parsed):
                raise forms.ValidationError("隐藏层神经元个数必须为正整数。")
        except ValueError:
            raise forms.ValidationError("隐藏层格式错误，请写成 64,32,16 这种形式。")
        return value