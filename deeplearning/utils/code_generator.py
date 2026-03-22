from typing import Dict, List


ACTIVATION_MAP = {
    "relu": "nn.ReLU()",
    "sigmoid": "nn.Sigmoid()",
    "tanh": "nn.Tanh()",
    "leaky_relu": "nn.LeakyReLU()",
}

OPTIMIZER_MAP = {
    "sgd": "optim.SGD",
    "adam": "optim.Adam",
    "adagrad": "optim.Adagrad",
    "rmsprop": "optim.RMSprop",
}

LOSS_MAP = {
    "mse": "nn.MSELoss()",
    "cross_entropy": "nn.CrossEntropyLoss()",
}



def parse_hidden_layers(raw: str) -> List[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]



def get_task_type(cfg: Dict) -> str:
    if cfg["dataset_source"] == "builtin":
        return "classification"
    return "classification" if cfg["synthetic_task"] == "normal_classification" else "regression"



def get_input_dim(cfg: Dict) -> int:
    if cfg["dataset_source"] == "builtin":
        mapping = {
            "mnist": 28 * 28,
            "fashion_mnist": 28 * 28,
            "cifar10": 3 * 32 * 32,
        }
        return mapping[cfg["builtin_dataset"]]
    return int(cfg["input_dim"])



def get_output_dim(cfg: Dict) -> int:
    task = get_task_type(cfg)
    if task == "regression":
        return 1
    if cfg["dataset_source"] == "builtin":
        return 10
    return 2



def get_loss_code(cfg: Dict) -> str:
    task = get_task_type(cfg)
    loss_function = cfg["loss_function"]
    if loss_function == "auto":
        return "nn.MSELoss()" if task == "regression" else "nn.CrossEntropyLoss()"
    return LOSS_MAP[loss_function]



def generate_dataset_code(cfg: Dict) -> List[str]:
    batch_size = cfg["batch_size"]
    if cfg["dataset_source"] == "builtin":
        dataset_name = cfg["builtin_dataset"]
        if dataset_name == "mnist":
            dataset_class = "datasets.MNIST"
        elif dataset_name == "fashion_mnist":
            dataset_class = "datasets.FashionMNIST"
        else:
            dataset_class = "datasets.CIFAR10"

        return [
            "transform = transforms.ToTensor()",
            f'train_dataset = {dataset_class}(root="data", train=True, download=True, transform=transform)',
            f'test_dataset = {dataset_class}(root="data", train=False, download=True, transform=transform)',
            f"train_loader = DataLoader(train_dataset, batch_size={batch_size}, shuffle=True)",
            f"test_loader = DataLoader(test_dataset, batch_size={batch_size}, shuffle=False)",
        ]

    n_samples = int(cfg["n_samples"])
    input_dim = int(cfg["input_dim"])
    noise_std = float(cfg["noise_std"])

    if cfg["synthetic_task"] == "normal_regression":
        return [
            f"X = torch.randn({n_samples}, {input_dim})",
            f"true_w = torch.randn({input_dim}, 1)",
            f"noise = {noise_std} * torch.randn({n_samples}, 1)",
            "y = X @ true_w + 2.0 + noise",
            "dataset = TensorDataset(X, y)",
            f"train_loader = DataLoader(dataset, batch_size={batch_size}, shuffle=True)",
        ]

    half = n_samples // 2
    remain = n_samples - half
    return [
        f"x0 = torch.randn({half}, {input_dim}) - 2.0",
        f"x1 = torch.randn({remain}, {input_dim}) + 2.0",
        "X = torch.cat([x0, x1], dim=0)",
        f"y = torch.cat([torch.zeros({half}, dtype=torch.long), torch.ones({remain}, dtype=torch.long)])",
        "dataset = TensorDataset(X, y)",
        f"train_loader = DataLoader(dataset, batch_size={batch_size}, shuffle=True)",
    ]



def generate_model_code(cfg: Dict) -> List[str]:
    input_dim = get_input_dim(cfg)
    output_dim = get_output_dim(cfg)

    if cfg["model_type"] == "custom_formula":
        formula = cfg.get("custom_formula", "y = w * x + b")
        return [
            "# 当前为自定义公式模式。为了安全，页面端只生成示意代码，不直接执行。",
            f"# 你的输入公式：{formula}",
            "class CustomModel(nn.Module):",
            "    def __init__(self):",
            "        super().__init__()",
            "        self.w = nn.Parameter(torch.randn(1))",
            "        self.b = nn.Parameter(torch.randn(1))",
            "",
            "    def forward(self, x):",
            "        return self.w * x + self.b",
            "",
            "model = CustomModel()",
        ]

    layers = []
    if cfg["dataset_source"] == "builtin":
        layers.append("nn.Flatten()")

    if cfg["model_type"] == "linear_model":
        layers.append(f"nn.Linear({input_dim}, {output_dim})")
    else:
        prev = input_dim
        hidden_layers = parse_hidden_layers(cfg["hidden_layers"])
        for hidden_dim in hidden_layers:
            layers.append(f"nn.Linear({prev}, {hidden_dim})")
            layers.append(ACTIVATION_MAP[cfg["activation"]])
            if float(cfg["dropout"]) > 0:
                layers.append(f"nn.Dropout({float(cfg['dropout'])})")
            prev = hidden_dim
        layers.append(f"nn.Linear({prev}, {output_dim})")

    lines = ["model = nn.Sequential("]
    lines.extend([f"    {layer}," for layer in layers])
    lines.append(")")
    return lines



def generate_train_loop_code(cfg: Dict) -> List[str]:
    task = get_task_type(cfg)
    lr = float(cfg["learning_rate"])
    epochs = int(cfg["epochs"])
    optimizer_cls = OPTIMIZER_MAP[cfg["optimizer"]]
    loss_code = get_loss_code(cfg)

    if task == "regression":
        target_expr = "y_batch"
        metrics_block = [
            "    avg_loss = total_loss / total_samples",
            '    print(f"epoch={epoch + 1:03d} loss={avg_loss:.6f}")',
        ]
    else:
        target_expr = "y_batch"
        metrics_block = [
            "    avg_loss = total_loss / total_samples",
            "    acc = total_correct / total_samples",
            '    print(f"epoch={epoch + 1:03d} loss={avg_loss:.6f} acc={acc:.4f}")',
        ]

    lines = [
        'device = torch.device("cuda" if torch.cuda.is_available() else "cpu")',
        "model = model.to(device)",
        f"criterion = {loss_code}",
        f"optimizer = {optimizer_cls}(model.parameters(), lr={lr})",
        "loss_history = []",
        "",
        f"for epoch in range({epochs}):",
        "    model.train()",
        "    total_loss = 0.0",
        "    total_correct = 0",
        "    total_samples = 0",
        "",
        "    for x_batch, y_batch in train_loader:",
        "        x_batch = x_batch.to(device)",
        f"        y_batch = {target_expr}.to(device)",
        "",
        "        pred = model(x_batch)",
    ]

    if task == "regression":
        lines.extend([
            "        loss = criterion(pred, y_batch)",
            "        total_samples += y_batch.size(0)",
        ])
    else:
        lines.extend([
            "        loss = criterion(pred, y_batch)",
            "        total_correct += (pred.argmax(dim=1) == y_batch).sum().item()",
            "        total_samples += y_batch.size(0)",
        ])

    lines.extend([
        "        optimizer.zero_grad()",
        "        loss.backward()",
        "        optimizer.step()",
        "        total_loss += loss.item() * y_batch.size(0)",
        "",
        "    loss_history.append(total_loss / total_samples)",
    ])
    lines.extend(metrics_block)
    lines.extend([
        "",
        "plt.plot(loss_history)",
        'plt.title("Training Loss")',
        'plt.xlabel("Epoch")',
        'plt.ylabel("Loss")',
        "plt.show()",
    ])
    return lines



def generate_pytorch_code(cfg: Dict) -> str:
    lines = [
        "import torch",
        "import torch.nn as nn",
        "import torch.optim as optim",
        "import matplotlib.pyplot as plt",
        "from torch.utils.data import DataLoader, TensorDataset",
    ]

    if cfg["dataset_source"] == "builtin":
        lines.append("from torchvision import datasets, transforms")

    lines.extend(["", "# ===== 1. 数据集 ====="])
    lines.extend(generate_dataset_code(cfg))
    lines.extend(["", "# ===== 2. 模型 ====="])
    lines.extend(generate_model_code(cfg))
    lines.extend(["", "# ===== 3. 训练 ====="])
    lines.extend(generate_train_loop_code(cfg))
    return "\n".join(lines)
