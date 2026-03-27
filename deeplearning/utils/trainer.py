import copy
import threading
import time
import traceback
import uuid
import ast

import numpy as np
import torch
import torch.nn as nn
from sklearn.datasets import load_breast_cancer, load_digits, load_iris
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

try:
    from torchvision import datasets, transforms
    HAS_TORCHVISION = True
except Exception:
    HAS_TORCHVISION = False


TRAINING_JOBS = {}
TRAINING_LOCK = threading.Lock()

DATASET_TASK_MAP = {
    "normal_regression": "regression",
    "normal_classification": "classification",
    "iris": "classification",
    "breast_cancer": "classification",
    "digits": "classification",
    "mnist": "classification",
    "fashion_mnist": "classification",
}


def start_training_job(config: dict) -> str:
    job_id = uuid.uuid4().hex
    device = "cuda" if torch.cuda.is_available() else "cpu"

    job_data = {
        "job_id": job_id,
        "status": "queued",
        "message": "训练任务已创建，等待启动。",
        "current_epoch": 0,
        "total_epochs": int(config["epochs"]),
        "device": device,
        "history": {
            "epoch": [],
            "train_loss": [],
            "test_loss": [],
            "train_acc": [],
            "test_acc": [],
        },
        "latest": {},
    }

    with TRAINING_LOCK:
        TRAINING_JOBS[job_id] = job_data

    thread = threading.Thread(
        target=_run_training_job,
        args=(job_id, config),
        daemon=True,
    )
    thread.start()
    return job_id


def get_training_job(job_id: str):
    with TRAINING_LOCK:
        job = TRAINING_JOBS.get(job_id)
        return copy.deepcopy(job) if job else None


def _update_job(job_id: str, **kwargs):
    with TRAINING_LOCK:
        if job_id in TRAINING_JOBS:
            TRAINING_JOBS[job_id].update(kwargs)


def _append_history(job_id: str, epoch, train_loss, test_loss, train_acc, test_acc):
    with TRAINING_LOCK:
        history = TRAINING_JOBS[job_id]["history"]
        history["epoch"].append(epoch)
        history["train_loss"].append(train_loss)
        history["test_loss"].append(test_loss)
        history["train_acc"].append(train_acc)
        history["test_acc"].append(test_acc)

        TRAINING_JOBS[job_id]["latest"] = {
            "train_loss": train_loss,
            "test_loss": test_loss,
            "train_acc": train_acc,
            "test_acc": test_acc,
        }


def _get_activation(name: str):
    if name == "relu":
        return nn.ReLU
    if name == "tanh":
        return nn.Tanh
    if name == "sigmoid":
        return nn.Sigmoid
    if name == "leaky_relu":
        return nn.LeakyReLU
    return nn.Identity


_ALLOWED_FORMULA_FUNCS = {
    "sin": torch.sin,
    "cos": torch.cos,
    "tanh": torch.tanh,
    "sigmoid": torch.sigmoid,
    "relu": torch.relu,
    "exp": torch.exp,
    "log": lambda x: torch.log(torch.clamp(x, min=1e-6)),
    "sqrt": lambda x: torch.sqrt(torch.clamp(x, min=1e-6)),
    "abs": torch.abs,
}

_ALLOWED_FORMULA_NAMES = {"x", "w", "b", "pi", *list(_ALLOWED_FORMULA_FUNCS.keys())}

_ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.MatMult,
    ast.UAdd,
    ast.USub,
    ast.Name,
    ast.Load,
    ast.Call,
    ast.Constant,
)


def _compile_formula(formula_text: str):
    expr = (formula_text or "x @ w + b").strip()

    if "=" in expr:
        left, right = expr.split("=", 1)
        if left.strip() == "y":
            expr = right.strip()

    tree = ast.parse(expr, mode="eval")

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_AST_NODES):
            raise RuntimeError(f"公式里包含暂不支持的语法：{type(node).__name__}")

        if isinstance(node, ast.Name) and node.id not in _ALLOWED_FORMULA_NAMES:
            raise RuntimeError(f"公式里包含未允许的变量或函数：{node.id}")

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FORMULA_FUNCS:
                raise RuntimeError("公式里只允许调用白名单函数，例如 sin、cos、tanh、relu 等。")
            if node.keywords:
                raise RuntimeError("自定义公式暂不支持关键字参数写法。")

    return compile(tree, "<custom_formula>", "eval"), expr


class FormulaModel(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, formula_text: str, task_type: str):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.task_type = task_type

        self.w = nn.Parameter(torch.randn(input_dim, output_dim) * 0.1)
        self.b = nn.Parameter(torch.zeros(output_dim))

        self._formula_code, self.formula_expr = _compile_formula(formula_text)

    def forward(self, x):
        env = {
            "x": x,
            "w": self.w,
            "b": self.b,
            "pi": torch.pi,
            **_ALLOWED_FORMULA_FUNCS,
        }

        y = eval(self._formula_code, {"__builtins__": {}}, env)

        if not torch.is_tensor(y):
            raise RuntimeError("自定义公式的输出不是张量。")

        if y.ndim == 1:
            y = y.unsqueeze(1)

        if self.task_type == "regression":
            if y.ndim != 2 or y.shape[1] != 1:
                raise RuntimeError(
                    f"回归任务要求公式输出形状为 [batch, 1]，当前得到 {tuple(y.shape)}。"
                )
        else:
            if y.ndim != 2 or y.shape[1] != self.output_dim:
                raise RuntimeError(
                    f"分类任务要求公式输出形状为 [batch, {self.output_dim}]，当前得到 {tuple(y.shape)}。"
                )

        return y

def _build_model(config, input_dim, output_dim, task_type):
    model_name = config["model_name"]

    if model_name == "linear":
        return nn.Linear(input_dim, output_dim)

    if model_name == "mlp":
        hidden_sizes = config.get("hidden_sizes_list", [])
        if not hidden_sizes:
            hidden_sizes = [64, 32]

        layers = []
        prev_dim = input_dim
        act_cls = _get_activation(config["activation"])
        dropout = float(config["dropout"])

        for hidden in hidden_sizes:
            layers.append(nn.Linear(prev_dim, hidden))
            layers.append(act_cls())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            prev_dim = hidden

        layers.append(nn.Linear(prev_dim, output_dim))
        return nn.Sequential(*layers)

    if model_name == "custom_formula":
        formula = config.get("custom_formula", "").strip() or "x @ w + b"
        return FormulaModel(
            input_dim=input_dim,
            output_dim=output_dim,
            formula_text=formula,
            task_type=task_type,
        )

    raise RuntimeError(f"暂不支持的模型类型：{model_name}")


def _build_optimizer(config, model):
    name = config["optimizer"]
    lr = float(config["learning_rate"])

    if name == "sgd":
        return torch.optim.SGD(model.parameters(), lr=lr)
    if name == "adam":
        return torch.optim.Adam(model.parameters(), lr=lr)
    if name == "adamw":
        return torch.optim.AdamW(model.parameters(), lr=lr)
    if name == "rmsprop":
        return torch.optim.RMSprop(model.parameters(), lr=lr)

    return torch.optim.Adam(model.parameters(), lr=lr)


def _prepare_x(x):
    if x.ndim > 2:
        x = x.view(x.size(0), -1)
    return x.float()


def _build_tabular_loaders(X, y, config, task_type):
    seed = int(config["random_seed"])
    test_size = float(config["test_size"])
    batch_size = int(config["batch_size"])
    normalize_data = bool(config.get("normalize_data", False))

    X_np = X.astype(np.float32)

    if task_type == "regression":
        y_np = y.astype(np.float32)
        X_train, X_test, y_train, y_test = train_test_split(
            X_np,
            y_np,
            test_size=test_size,
            random_state=seed,
        )
    else:
        y_np = y.astype(np.int64)
        X_train, X_test, y_train, y_test = train_test_split(
            X_np,
            y_np,
            test_size=test_size,
            random_state=seed,
            stratify=y_np,
        )

    X_train = torch.tensor(X_train, dtype=torch.float32)
    X_test = torch.tensor(X_test, dtype=torch.float32)

    if normalize_data:
        mean = X_train.mean(dim=0, keepdim=True)
        std = X_train.std(dim=0, keepdim=True).clamp_min(1e-6)
        X_train = (X_train - mean) / std
        X_test = (X_test - mean) / std

    if task_type == "regression":
        y_train = torch.tensor(y_train, dtype=torch.float32)
        y_test = torch.tensor(y_test, dtype=torch.float32)

        if y_train.ndim == 1:
            y_train = y_train.unsqueeze(1)
        if y_test.ndim == 1:
            y_test = y_test.unsqueeze(1)

        output_dim = 1
    else:
        y_train = torch.tensor(y_train, dtype=torch.long)
        y_test = torch.tensor(y_test, dtype=torch.long)
        output_dim = int(max(y_train.max().item(), y_test.max().item()) + 1)

    train_loader = DataLoader(
        TensorDataset(X_train, y_train),
        batch_size=batch_size,
        shuffle=True,
        pin_memory=torch.cuda.is_available(),
    )
    test_loader = DataLoader(
        TensorDataset(X_test, y_test),
        batch_size=batch_size,
        shuffle=False,
        pin_memory=torch.cuda.is_available(),
    )

    input_dim = X_train.shape[1]
    return train_loader, test_loader, input_dim, output_dim


def _load_dataset(config):
    dataset_name = config["dataset_name"]
    task_type = DATASET_TASK_MAP[dataset_name]

    seed = int(config["random_seed"])
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    if dataset_name == "normal_regression":
        num_samples = int(config["num_samples"])
        input_dim = int(config["input_dim"])
        noise_std = float(config["noise_std"])

        X = np.random.randn(num_samples, input_dim).astype(np.float32)
        true_w = np.random.randn(input_dim, 1).astype(np.float32)
        true_b = np.random.randn(1).astype(np.float32)
        y = X @ true_w + true_b + noise_std * np.random.randn(num_samples, 1).astype(np.float32)

        return (*_build_tabular_loaders(X, y, config, task_type), task_type)

    if dataset_name == "normal_classification":
        num_samples = int(config["num_samples"])
        input_dim = int(config["input_dim"])
        noise_std = float(config["noise_std"])
        num_classes = int(config["num_classes"])

        X = np.random.randn(num_samples, input_dim).astype(np.float32)
        W = np.random.randn(input_dim, num_classes).astype(np.float32)
        b = np.random.randn(num_classes).astype(np.float32)
        logits = X @ W + b + noise_std * np.random.randn(num_samples, num_classes).astype(np.float32)
        y = np.argmax(logits, axis=1).astype(np.int64)

        return (*_build_tabular_loaders(X, y, config, task_type), task_type)

    if dataset_name == "iris":
        data = load_iris()
        return (*_build_tabular_loaders(data.data, data.target, config, task_type), task_type)

    if dataset_name == "breast_cancer":
        data = load_breast_cancer()
        return (*_build_tabular_loaders(data.data, data.target, config, task_type), task_type)

    if dataset_name == "digits":
        data = load_digits()
        X = data.data.astype(np.float32) / 16.0
        y = data.target.astype(np.int64)
        return (*_build_tabular_loaders(X, y, config, task_type), task_type)

    if dataset_name in ["mnist", "fashion_mnist"]:
        if not HAS_TORCHVISION:
            raise RuntimeError("当前环境未安装 torchvision，无法加载 MNIST / FashionMNIST。")

        transform = transforms.ToTensor()

        if dataset_name == "mnist":
            train_dataset = datasets.MNIST(root="data", train=True, download=True, transform=transform)
            test_dataset = datasets.MNIST(root="data", train=False, download=True, transform=transform)
        else:
            train_dataset = datasets.FashionMNIST(root="data", train=True, download=True, transform=transform)
            test_dataset = datasets.FashionMNIST(root="data", train=False, download=True, transform=transform)

        batch_size = int(config["batch_size"])
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            pin_memory=torch.cuda.is_available(),
        )
        test_loader = DataLoader(
            test_dataset,
            batch_size=batch_size,
            shuffle=False,
            pin_memory=torch.cuda.is_available(),
        )
        input_dim = 28 * 28
        output_dim = 10
        return train_loader, test_loader, input_dim, output_dim, task_type

    raise RuntimeError("暂不支持该数据集。")


def _evaluate(model, loader, criterion, task_type, device):
    model.eval()
    total_loss = 0.0
    total_samples = 0
    correct = 0

    with torch.no_grad():
        for xb, yb in loader:
            xb = _prepare_x(xb).to(device, non_blocking=True)
            yb = yb.to(device, non_blocking=True)

            pred = model(xb)
            loss = criterion(pred, yb)
            total_loss += loss.item() * xb.size(0)
            total_samples += xb.size(0)

            if task_type == "classification":
                correct += (pred.argmax(dim=1) == yb).sum().item()

    avg_loss = total_loss / max(total_samples, 1)

    if task_type == "classification":
        acc = correct / max(total_samples, 1)
    else:
        acc = None

    return avg_loss, acc


def _run_training_job(job_id: str, config: dict):
    try:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        _update_job(
            job_id,
            status="running",
            device=str(device),
            message=f"训练已开始，当前设备：{device}",
        )

        train_loader, test_loader, input_dim, output_dim, task_type = _load_dataset(config)
        model = _build_model(config, input_dim, output_dim, task_type).to(device)
        optimizer = _build_optimizer(config, model)

        if task_type == "regression":
            criterion = nn.MSELoss()
        else:
            criterion = nn.CrossEntropyLoss()

        epochs = int(config["epochs"])

        for epoch in range(1, epochs + 1):
            model.train()
            train_loss_sum = 0.0
            train_samples = 0
            train_correct = 0

            for xb, yb in train_loader:
                xb = _prepare_x(xb).to(device, non_blocking=True)
                yb = yb.to(device, non_blocking=True)

                optimizer.zero_grad()
                pred = model(xb)
                loss = criterion(pred, yb)
                loss.backward()
                optimizer.step()

                batch_size = xb.size(0)
                train_loss_sum += loss.item() * batch_size
                train_samples += batch_size

                if task_type == "classification":
                    train_correct += (pred.argmax(dim=1) == yb).sum().item()

            train_loss = train_loss_sum / max(train_samples, 1)

            if task_type == "classification":
                train_acc = train_correct / max(train_samples, 1)
            else:
                train_acc = None

            test_loss, test_acc = _evaluate(model, test_loader, criterion, task_type, device)

            _append_history(
                job_id=job_id,
                epoch=epoch,
                train_loss=float(train_loss),
                test_loss=float(test_loss),
                train_acc=(float(train_acc) if train_acc is not None else None),
                test_acc=(float(test_acc) if test_acc is not None else None),
            )

            _update_job(
                job_id,
                current_epoch=epoch,
                message=f"第 {epoch}/{epochs} 轮训练完成，当前设备：{device}",
            )

            # 这一句原来是 0.15，会明显拖慢训练
            time.sleep(0.02)

        _update_job(
            job_id,
            status="finished",
            message=f"训练完成，使用设备：{device}",
        )

    except Exception as e:
        _update_job(
            job_id,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            traceback=traceback.format_exc(),
        )