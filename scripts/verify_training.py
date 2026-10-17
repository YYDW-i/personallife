"""对全部离线数据集与三种模型各运行一轮真实 CPU 训练。"""
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("LOCALLIFE_DATA_DIR", str(ROOT / ".runtime-training-check"))

import django
django.setup()
import torch
from deeplearning.forms import DEFAULT_FORM_DATA
from deeplearning.views import _normalize_config
from deeplearning.utils.trainer import start_training_job, get_training_job, TRAINING_JOBS

torch.set_num_threads(2)
count = 0
for dataset in ("normal_regression", "normal_classification", "iris", "breast_cancer", "digits"):
    for model in ("linear", "mlp", "custom_formula"):
        config = _normalize_config({**DEFAULT_FORM_DATA, "dataset_name": dataset, "model_name": model,
                                   "epochs": 1, "num_samples": 100, "custom_formula": "y = x @ w + b"})
        job_id = start_training_job(config, user_id=1)
        deadline = time.monotonic() + 60
        while True:
            job = get_training_job(job_id, user_id=1)
            if job["status"] in ("finished", "error"):
                break
            if time.monotonic() > deadline:
                raise RuntimeError(f"训练超时：{dataset}/{model}")
            time.sleep(.05)
        assert job["status"] == "finished", (dataset, model, job["message"])
        assert math.isfinite(job["latest"]["train_loss"])
        assert math.isfinite(job["latest"]["test_loss"])
        TRAINING_JOBS.pop(job_id, None)
        count += 1
print(f"OFFLINE_TRAINING_OK: {count} dataset/model combinations on CPU")
