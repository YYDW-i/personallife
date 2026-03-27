def _activation_code(name: str) -> str:
    mapping = {
        "relu": "nn.ReLU()",
        "tanh": "nn.Tanh()",
        "sigmoid": "nn.Sigmoid()",
        "leaky_relu": "nn.LeakyReLU()",
        "none": "nn.Identity()",
    }
    return mapping.get(name, "nn.ReLU()")


def _optimizer_code(name: str, lr: float) -> str:
    mapping = {
        "sgd": f"torch.optim.SGD(model.parameters(), lr={lr})",
        "adam": f"torch.optim.Adam(model.parameters(), lr={lr})",
        "adamw": f"torch.optim.AdamW(model.parameters(), lr={lr})",
        "rmsprop": f"torch.optim.RMSprop(model.parameters(), lr={lr})",
    }
    return mapping.get(name, f"torch.optim.Adam(model.parameters(), lr={lr})")


def _dataset_code(config: dict) -> str:
    name = config["dataset_name"]
    test_size = config["test_size"]
    batch_size = config["batch_size"]
    seed = config["random_seed"]
    normalize_data = config.get("normalize_data", False)

    if name == "normal_regression":
        return f"""
# 1. 构造随机正态分布回归数据
num_samples = {config["num_samples"]}
input_dim = {config["input_dim"]}
noise_std = {config["noise_std"]}

torch.manual_seed({seed})
X = torch.randn(num_samples, input_dim)
true_w = torch.randn(input_dim, 1)
true_b = torch.randn(1)
y = X @ true_w + true_b + noise_std * torch.randn(num_samples, 1)

X_train, X_test, y_train, y_test = train_test_split(
    X.numpy(), y.numpy(), test_size={test_size}, random_state={seed}
)

X_train = torch.tensor(X_train, dtype=torch.float32)
X_test = torch.tensor(X_test, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.float32)
y_test = torch.tensor(y_test, dtype=torch.float32)

if {normalize_data}:
    mean = X_train.mean(dim=0, keepdim=True)
    std = X_train.std(dim=0, keepdim=True).clamp_min(1e-6)
    X_train = (X_train - mean) / std
    X_test = (X_test - mean) / std

train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size={batch_size}, shuffle=True)
test_loader = DataLoader(TensorDataset(X_test, y_test), batch_size={batch_size}, shuffle=False)

task_type = "regression"
output_dim = 1
"""

    if name == "normal_classification":
        return f"""
# 1. 构造随机正态分布分类数据
num_samples = {config["num_samples"]}
input_dim = {config["input_dim"]}
noise_std = {config["noise_std"]}
num_classes = {config["num_classes"]}

torch.manual_seed({seed})
X = torch.randn(num_samples, input_dim)
W = torch.randn(input_dim, num_classes)
b = torch.randn(num_classes)
logits = X @ W + b + noise_std * torch.randn(num_samples, num_classes)
y = torch.argmax(logits, dim=1)

X_train, X_test, y_train, y_test = train_test_split(
    X.numpy(),
    y.numpy(),
    test_size={test_size},
    random_state={seed},
    stratify=y.numpy()
)

X_train = torch.tensor(X_train, dtype=torch.float32)
X_test = torch.tensor(X_test, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.long)
y_test = torch.tensor(y_test, dtype=torch.long)

if {normalize_data}:
    mean = X_train.mean(dim=0, keepdim=True)
    std = X_train.std(dim=0, keepdim=True).clamp_min(1e-6)
    X_train = (X_train - mean) / std
    X_test = (X_test - mean) / std

train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size={batch_size}, shuffle=True)
test_loader = DataLoader(TensorDataset(X_test, y_test), batch_size={batch_size}, shuffle=False)

task_type = "classification"
output_dim = num_classes
"""

    if name == "iris":
        return f"""
# 1. 加载 Iris 数据集
data = load_iris()
X = data.data.astype("float32")
y = data.target.astype("int64")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size={test_size}, random_state={seed}, stratify=y
)

X_train = torch.tensor(X_train, dtype=torch.float32)
X_test = torch.tensor(X_test, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.long)
y_test = torch.tensor(y_test, dtype=torch.long)

if {normalize_data}:
    mean = X_train.mean(dim=0, keepdim=True)
    std = X_train.std(dim=0, keepdim=True).clamp_min(1e-6)
    X_train = (X_train - mean) / std
    X_test = (X_test - mean) / std

train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size={batch_size}, shuffle=True)
test_loader = DataLoader(TensorDataset(X_test, y_test), batch_size={batch_size}, shuffle=False)

input_dim = X_train.shape[1]
task_type = "classification"
output_dim = 3
"""

    if name == "breast_cancer":
        return f"""
# 1. 加载 Breast Cancer 数据集
data = load_breast_cancer()
X = data.data.astype("float32")
y = data.target.astype("int64")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size={test_size}, random_state={seed}, stratify=y
)

X_train = torch.tensor(X_train, dtype=torch.float32)
X_test = torch.tensor(X_test, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.long)
y_test = torch.tensor(y_test, dtype=torch.long)

if {normalize_data}:
    mean = X_train.mean(dim=0, keepdim=True)
    std = X_train.std(dim=0, keepdim=True).clamp_min(1e-6)
    X_train = (X_train - mean) / std
    X_test = (X_test - mean) / std

train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size={batch_size}, shuffle=True)
test_loader = DataLoader(TensorDataset(X_test, y_test), batch_size={batch_size}, shuffle=False)

input_dim = X_train.shape[1]
task_type = "classification"
output_dim = 2
"""

    if name == "digits":
        return f"""
# 1. 加载 Digits 数据集
data = load_digits()
X = (data.data / 16.0).astype("float32")
y = data.target.astype("int64")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size={test_size}, random_state={seed}, stratify=y
)

X_train = torch.tensor(X_train, dtype=torch.float32)
X_test = torch.tensor(X_test, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.long)
y_test = torch.tensor(y_test, dtype=torch.long)

if {normalize_data}:
    mean = X_train.mean(dim=0, keepdim=True)
    std = X_train.std(dim=0, keepdim=True).clamp_min(1e-6)
    X_train = (X_train - mean) / std
    X_test = (X_test - mean) / std

train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size={batch_size}, shuffle=True)
test_loader = DataLoader(TensorDataset(X_test, y_test), batch_size={batch_size}, shuffle=False)

input_dim = X_train.shape[1]
task_type = "classification"
output_dim = 10
"""

    if name == "mnist":
        return f"""
# 1. 加载 MNIST 数据集
from torchvision import datasets, transforms

transform = transforms.ToTensor()

train_dataset = datasets.MNIST(root="data", train=True, download=True, transform=transform)
test_dataset = datasets.MNIST(root="data", train=False, download=True, transform=transform)

train_loader = DataLoader(train_dataset, batch_size={batch_size}, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size={batch_size}, shuffle=False)

input_dim = 28 * 28
task_type = "classification"
output_dim = 10
"""

    if name == "fashion_mnist":
        return f"""
# 1. 加载 FashionMNIST 数据集
from torchvision import datasets, transforms

transform = transforms.ToTensor()

train_dataset = datasets.FashionMNIST(root="data", train=True, download=True, transform=transform)
test_dataset = datasets.FashionMNIST(root="data", train=False, download=True, transform=transform)

train_loader = DataLoader(train_dataset, batch_size={batch_size}, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size={batch_size}, shuffle=False)

input_dim = 28 * 28
task_type = "classification"
output_dim = 10
"""

    return "# 暂不支持该数据集"


def _model_code(config: dict) -> str:
    model_name = config["model_name"]
    activation = _activation_code(config["activation"])
    dropout = config["dropout"]
    hidden_sizes = config.get("hidden_sizes_list", [])

    if model_name == "linear":
        return """
# 2. 构造模型
model = nn.Linear(input_dim, output_dim)
"""

    if model_name == "custom_formula":
        formula = (config.get("custom_formula", "") or "x @ w + b").strip()
        if "=" in formula:
            left, right = formula.split("=", 1)
            if left.strip() == "y":
                formula = right.strip()

        return f'''
    # 2. 构造自定义公式模型
    sin = torch.sin
    cos = torch.cos
    tanh = torch.tanh
    sigmoid = torch.sigmoid
    relu = torch.relu
    exp = torch.exp
    log = lambda x: torch.log(torch.clamp(x, min=1e-6))
    sqrt = lambda x: torch.sqrt(torch.clamp(x, min=1e-6))
    abs = torch.abs
    pi = torch.pi

    class CustomFormulaModel(nn.Module):
        def __init__(self, input_dim, output_dim, task_type):
            super().__init__()
            self.output_dim = output_dim
            self.task_type = task_type
            self.w = nn.Parameter(torch.randn(input_dim, output_dim) * 0.1)
            self.b = nn.Parameter(torch.zeros(output_dim))

        def forward(self, x):
            y = {formula}
            if y.ndim == 1:
                y = y.unsqueeze(1)

            if self.task_type == "regression" and y.shape[1] != 1:
                raise RuntimeError(f"回归任务要求输出形状为 [batch, 1]，当前为 {{tuple(y.shape)}}")
            if self.task_type == "classification" and y.shape[1] != self.output_dim:
                raise RuntimeError(f"分类任务要求输出形状为 [batch, {{self.output_dim}}]，当前为 {{tuple(y.shape)}}")

            return y

    model = CustomFormulaModel(input_dim, output_dim, task_type)
    '''

    hidden_sizes = hidden_sizes or [64, 32]
    hidden_text = ", ".join(str(x) for x in hidden_sizes)

    return f"""
# 2. 构造 MLP 模型
layers = []
prev_dim = input_dim
hidden_sizes = [{hidden_text}]

for hidden in hidden_sizes:
    layers.append(nn.Linear(prev_dim, hidden))
    layers.append({activation})
    if {dropout} > 0:
        layers.append(nn.Dropout({dropout}))
    prev_dim = hidden

layers.append(nn.Linear(prev_dim, output_dim))
model = nn.Sequential(*layers)
"""


def generate_pytorch_code(config: dict) -> str:
    dataset_name = config["dataset_name"]
    optimizer_code = _optimizer_code(config["optimizer"], config["learning_rate"])
    dataset_section = _dataset_code(config)
    model_section = _model_code(config)

    extra_import = ""
    if dataset_name in ["mnist", "fashion_mnist"]:
        extra_import = "from torchvision import datasets, transforms\n"

    return f'''import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.datasets import load_iris, load_breast_cancer, load_digits

{extra_import}
# =========================
# DeepLearning 模块自动生成 PyTorch 示例代码
# =========================

{dataset_section}

{model_section}

# 3. 定义损失函数与优化器
if task_type == "regression":
    criterion = nn.MSELoss()
else:
    criterion = nn.CrossEntropyLoss()

optimizer = {optimizer_code}
epochs = {config["epochs"]}

train_loss_list = []
test_loss_list = []
train_acc_list = []
test_acc_list = []

def prepare_x(x):
    if x.ndim > 2:
        x = x.view(x.size(0), -1)
    return x.float()

def evaluate(loader):
    model.eval()
    total_loss = 0.0
    total_samples = 0
    correct = 0

    with torch.no_grad():
        for xb, yb in loader:
            xb = prepare_x(xb)
            pred = model(xb)
            loss = criterion(pred, yb)
            total_loss += loss.item() * xb.size(0)
            total_samples += xb.size(0)

            if task_type == "classification":
                correct += (pred.argmax(dim=1) == yb).sum().item()

    avg_loss = total_loss / total_samples
    if task_type == "classification":
        acc = correct / total_samples
    else:
        acc = float("nan")

    return avg_loss, acc

# 4. 开始训练
for epoch in range(1, epochs + 1):
    model.train()
    train_loss_sum = 0.0
    train_samples = 0
    train_correct = 0

    for xb, yb in train_loader:
        xb = prepare_x(xb)

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

    train_loss = train_loss_sum / train_samples

    if task_type == "classification":
        train_acc = train_correct / train_samples
    else:
        train_acc = float("nan")

    test_loss, test_acc = evaluate(test_loader)

    train_loss_list.append(train_loss)
    test_loss_list.append(test_loss)
    train_acc_list.append(train_acc)
    test_acc_list.append(test_acc)

    print(
        f"Epoch {{epoch:03d}} | "
        f"Train Loss={{train_loss:.4f}} | Test Loss={{test_loss:.4f}} | "
        f"Train Acc={{train_acc if train_acc == train_acc else 'N/A'}} | "
        f"Test Acc={{test_acc if test_acc == test_acc else 'N/A'}}"
    )

# 5. 可视化训练过程
epochs_x = list(range(1, epochs + 1))

plt.figure(figsize=(10, 6))
plt.plot(epochs_x, train_loss_list, label="Train Loss", color="royalblue", linewidth=2)
plt.plot(epochs_x, test_loss_list, label="Test Loss", color="orange", linewidth=2)
plt.plot(epochs_x, train_acc_list, label="Train Acc", color="green", linewidth=2)
plt.plot(epochs_x, test_acc_list, label="Test Acc", color="red", linewidth=2)

plt.xlabel("Epoch")
plt.ylabel("Metric")
plt.title("Training Process")
plt.legend()
plt.grid(alpha=0.3)
plt.show()
'''