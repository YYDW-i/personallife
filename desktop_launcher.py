"""LocalLife Windows 启动入口，同时支持源码运行与 PyInstaller 目录发行包。"""
import argparse
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
import threading
import time
import webbrowser


def default_data_dir():
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        # 从本仓库生成的发行包直接沿用项目数据；拷走整个发行目录后使用 userdata。
        project_dir = executable_dir.parent.parent
        if (project_dir / "manage.py").is_file() and (project_dir / "desktop_launcher.py").is_file():
            return project_dir
        return executable_dir / "userdata"
    return Path(__file__).resolve().parent


def acquire_instance(data_dir):
    """操作系统文件锁随进程退出自动释放，避免残留 PID 阻止启动。"""
    import msvcrt
    handle = (data_dir / ".desktop.lock").open("a+b")
    # 已运行实例锁住第一个字节后，Windows 连读取该字节也会拒绝。
    # 只查询文件长度，避免重复双击在尝试加锁之前就抛出 PermissionError。
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        return None
    return handle


def migrate_safely(data_dir):
    from django.core.management import call_command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
    database = data_dir / "db.sqlite3"
    if pending and database.exists() and database.stat().st_size:
        backup_dir = data_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup = backup_dir / f"db-before-migrate-{time.time_ns()}.sqlite3"
        with sqlite3.connect(database) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        print(f"数据库已备份：{backup}")
    call_command("migrate", interactive=False, verbosity=0)
    from news.models import NewsSource
    if not NewsSource.objects.exists():
        # 只为没有新闻源的数据目录初始化默认订阅，不覆盖用户配置；此步骤不联网。
        call_command("seed_news_sources", verbosity=0)


def smoke_test():
    """仅在专用空数据目录运行；验收冻结包的动态导入、模板与数学/训练依赖。"""
    from django.contrib.auth import get_user_model
    from django.test import Client
    from maths.engine import diff_expr, plot_2d
    from deeplearning.utils.trainer import start_training_job, get_training_job
    from deeplearning.forms import DEFAULT_FORM_DATA
    from deeplearning.views import _normalize_config

    user = get_user_model().objects.create_user(username="desktop_smoke", password="Smoke-test-2026!")
    client = Client()
    client.force_login(user)
    try:
        for route in ("/", "/tasks/", "/tasks/new/", "/calendar/", "/news/", "/maths/",
                      "/deeplearning/", "/analytics/iching/", "/settings/", "/players/profile/"):
            response = client.get(route)
            if response.status_code != 200:
                raise RuntimeError(f"页面验收失败：{route}: {response.status_code}")
        assert diff_expr("x^2")["result_str"] == "2*x"
        assert plot_2d("3")["img_base64"]
        config = _normalize_config({**DEFAULT_FORM_DATA, "epochs": 1, "num_samples": 100})
        job_id = start_training_job(config, user_id=user.pk)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            job = get_training_job(job_id, user_id=user.pk)
            if job["status"] in ("finished", "error", "failed"):
                if job["status"] != "finished":
                    raise RuntimeError(job["message"])
                break
            time.sleep(.2)
        else:
            raise RuntimeError("训练验收超时")
        print("SMOKE_TEST_OK: 10 pages, symbolic math, constant plot, real CPU training")
    finally:
        user.delete()


def main():
    parser = argparse.ArgumentParser(description="LocalLife 一键启动")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("端口范围为 1~65535")
    if args.smoke_test and (not args.data_dir or (args.data_dir / "db.sqlite3").exists()):
        parser.error("--smoke-test 必须指定一个尚无数据库的独立 --data-dir")
    data_dir = (args.data_dir or default_data_dir()).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["LOCALLIFE_DATA_DIR"] = str(data_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ.setdefault("MPLBACKEND", "Agg")
    # 冻结后标准输出也强制使用 UTF-8，日志可直接用中文编辑器查看。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(filename=data_dir / "desktop.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s", encoding="utf-8")
    lock = acquire_instance(data_dir)
    instance_path = data_dir / ".desktop-instance.json"
    if lock is None:
        # 第一次启动可能还在初始化，等待实例地址写入。
        for _ in range(150):
            try:
                info = json.loads(instance_path.read_text(encoding="utf-8"))
                url = info["url"]
                if not url.startswith("http://127.0.0.1:"):
                    raise ValueError("实例地址无效")
                if not args.no_browser:
                    webbrowser.open(url)
                print(f"LocalLife 已在运行：{url}")
                return
            except (OSError, ValueError, KeyError):
                time.sleep(.2)
        raise RuntimeError("已有实例正在启动，请稍后重试。")
    try:
        instance_path.unlink(missing_ok=True)
        print("LocalLife 2.0 · 正在准备你的个人空间…", flush=True)
        import django
        django.setup()
        migrate_safely(data_dir)
        if args.smoke_test:
            smoke_test()
            return
        from django.core.wsgi import get_wsgi_application
        from django.contrib.staticfiles.handlers import StaticFilesHandler
        from waitress import create_server

        application = StaticFilesHandler(get_wsgi_application())
        server = None
        for port in range(args.port, min(args.port + 30, 65536)):
            try:
                server = create_server(application, host="127.0.0.1", port=port, threads=4)
                break
            except OSError as error:
                if getattr(error, "winerror", None) not in (10048, 10013) and error.errno not in (10048, 10013):
                    raise
        if server is None:
            raise RuntimeError("无法监听本地端口，请检查端口占用或本机网络权限，或使用 --port 指定其他端口。")
        url = f"http://127.0.0.1:{port}/"
        instance_path.write_text(json.dumps({"url": url, "pid": os.getpid()}), encoding="utf-8")
        print(f"\n服务已启动：{url}\n数据目录：{data_dir}\n关闭此窗口或按 Ctrl+C 可停止服务。", flush=True)
        if not args.no_browser:
            threading.Timer(.8, lambda: webbrowser.open(url)).start()
        try:
            server.run()
        finally:
            server.close()
    finally:
        instance_path.unlink(missing_ok=True)
        lock.close()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as error:
        logging.exception("LocalLife 启动失败")
        print(f"启动失败：{error}\n详情请查看数据目录中的 desktop.log。", file=sys.stderr)
        if getattr(sys, "frozen", False) and "--no-browser" not in sys.argv:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"启动失败：{error}\n请查看数据目录中的 desktop.log。", "LocalLife", 0x10)
        sys.exit(1)
