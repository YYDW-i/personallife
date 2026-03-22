import base64
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset


ACTIVATION_MAP = {
    "relu": nn.ReLU,
    "sigmoid": nn.Sigmoid,
    "tanh": nn.Tanh,
    "leaky_relu": nn.LeakyReLU,
}

OPTIMIZER_MAP = {
    "sgd": optim.SGD,
    "adam": optim.Adam,
    "adagrad": optim.Adagrad,
    "rmsprop": optim.RMSprop,
}



def parse_hidden_layers(raw: str) -> List[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]



def get_task_type(cfg: Dict) -> str:
    if cfg["dataset_source"] == "builtin":
        return "classification"
    return "classification" if cfg["synthetic_task"] == "normal_classification" else "regression"



def build_model(cfg: Dict, input_dim: int, output_dim: int) -> nn.Module:
    layers = []
    model_type = cfg["model_type"]

    if model_type == "linear_model":
        return nn.Sequential(nn.Linear(input_dim, output_dim))

    hidden_layers = parse_hidden_layers(cfg["hidden_layers"])
    activation_cls = ACTIVATION_MAP[cfg["activation"]]
    prev = input_dim
    for hidden_dim in hidden_layers:
        layers.append(nn.Linear(prev, hidden_dim))
        layers.append(activation_cls())
        if float(cfg["dropout"]) > 0:
            layers.append(nn.Dropout(float(cfg["dropout"])))
        prev = hidden_dim
    layers.append(nn.Linear(prev, output_dim))
    return nn.Sequential(*layers)



def generate_synthetic_regression(cfg: Dict) -> Tuple[torch.Tensor, torch.Tensor]:
    n_samples = int(cfg["n_samples"])
    input_dim = int(cfg["input_dim"])
    noise_std = float(cfg["noise_std"])

    X = torch.randn(n_samples, input_dim)
    true_w = torch.randn(input_dim, 1)
    y = X @ true_w + 2.0 + noise_std * torch.randn(n_samples, 1)
    return X, y



def generate_synthetic_classification(cfg: Dict) -> Tuple[torch.Tensor, torch.Tensor]:
    n_samples = int(cfg["n_samples"])
    input_dim = int(cfg["input_dim"])
    half = n_samples // 2
    remain = n_samples - half

    x0 = torch.randn(half, input_dim) - 2.0
    x1 = torch.randn(remain, input_dim) + 2.0
    X = torch.cat([x0, x1], dim=0)
    y = torch.cat([
        torch.zeros(half, dtype=torch.long),
        torch.ones(remain, dtype=torch.long),
    ])
    return X, y



def get_criterion(cfg: Dict, task: str):
    if cfg["loss_function"] == "auto":
        return nn.MSELoss() if task == "regression" else nn.CrossEntropyLoss()
    if cfg["loss_function"] == "mse":
        return nn.MSELoss()
    return nn.CrossEntropyLoss()



def build_optimizer(cfg: Dict, model: nn.Module):
    optimizer_cls = OPTIMIZER_MAP[cfg["optimizer"]]
    return optimizer_cls(model.parameters(), lr=float(cfg["learning_rate"]))



def plot_to_base64(loss_history: List[float]) -> str:
    fig = plt.figure(figsize=(7, 4))
    plt.plot(loss_history)
    plt.title("Training Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")



def train_demo(cfg: Dict) -> Tuple[Optional[str], Dict]:
    if cfg["dataset_source"] != "synthetic":
        return None, {
            "message": "当前页面中的演示训练只支持随机合成数据。内置公开数据集部分已支持代码生成，你可以复制代码到本地运行。"
        }

    if cfg["model_type"] == "custom_formula":
        return None, {
            "message": "自定义公式模式当前只做代码生成，不在服务器端直接执行。"
        }

    task = get_task_type(cfg)
    if task == "regression":
        X, y = generate_synthetic_regression(cfg)
        output_dim = 1
    else:
        X, y = generate_synthetic_classification(cfg)
        output_dim = 2

    dataset = TensorDataset(X, y)
    loader = DataLoader(dataset, batch_size=int(cfg["batch_size"]), shuffle=True)

    model = build_model(cfg, input_dim=X.shape[1], output_dim=output_dim)
    criterion = get_criterion(cfg, task)
    optimizer = build_optimizer(cfg, model)

    epochs = int(cfg["epochs"])
    loss_history: List[float] = []
    final_acc = None

    for _ in range(epochs):
        model.train()
        total_loss = 0.0
        total_samples = 0
        total_correct = 0

        for xb, yb in loader:
            pred = model(xb)
            if task == "regression":
                loss = criterion(pred, yb)
            else:
                loss = criterion(pred, yb)
                total_correct += (pred.argmax(dim=1) == yb).sum().item()

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * yb.size(0)
            total_samples += yb.size(0)

        avg_loss = total_loss / max(total_samples, 1)
        loss_history.append(avg_loss)
        if task == "classification":
            final_acc = total_correct / max(total_samples, 1)

    plot_base64 = plot_to_base64(loss_history)
    summary = {
        "message": "演示训练已完成。",
        "task": "回归" if task == "regression" else "分类",
        "final_loss": round(loss_history[-1], 6) if loss_history else None,
        "final_acc": round(final_acc, 4) if final_acc is not None else None,
    }
    return plot_base64, summary
