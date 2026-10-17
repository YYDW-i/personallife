"""验证 EXE 的 HTTP 服务、静态文件、端口避让与重复启动。只写专用验收目录。"""
import argparse
from http.cookiejar import CookieJar
import json
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time
import urllib.request
from urllib.parse import urlencode


def verify_user_flow(url):
    cookies = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

    def get(path):
        with opener.open(url + path, timeout=15) as response:
            assert response.status == 200
            return response.read().decode("utf-8")

    def csrf():
        return next(cookie.value for cookie in cookies if cookie.name == "csrftoken")

    def post(path, data):
        body = urlencode({**data, "csrfmiddlewaretoken": csrf()}).encode()
        with opener.open(url + path, data=body, timeout=15) as response:
            assert response.status == 200
            return response.read().decode("utf-8")

    get("accounts/register/")
    html = post("accounts/register/", {"username": "desktop_http_test", "email": "",
                                       "password1": "Desktop-test-2026!", "password2": "Desktop-test-2026!"})
    assert "总览工作台" in html and any(cookie.name == "sessionid" for cookie in cookies)
    post("tasks/new/", {"title": "桌面端验收任务", "description": "隔离的测试数据",
                         "schedule_kind": "NONE", "remind_lead_minutes": 0})
    html = get("tasks/")
    assert "桌面端验收任务" in html
    task_id = re.search(r'href="/tasks/(\d+)/edit/"', html).group(1)
    html = post(f"tasks/{task_id}/complete/", {})
    assert "已完成" in html
    request = urllib.request.Request(url + "maths/api/run/", method="POST",
        data=json.dumps({"mode": "diff", "expr": "x^3"}).encode(),
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf()})
    with opener.open(request, timeout=15) as response:
        assert json.load(response)["data"]["result_str"] == "3*x**2"
    html = post("settings/", {"height_cm": "175", "weight_kg": "65", "age_year": "25", "gender": "M",
                               "exercise_frequency": "3", "exercise_time_minutes": "30", "sleep_hours": "7.5"})
    assert "21.2" in html
    post("accounts/logout/", {})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--source", action="store_true", help="使用指定 Python 验证源码启动器")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    executable = args.executable.resolve()
    data_dir = Path(tempfile.mkdtemp(prefix=".runtime-http-", dir=root))
    with socket.socket() as occupied, (data_dir / "verification.log").open("w", encoding="utf-8") as log:
        # 固定使用应用端口范围，避开 Windows 可能保留的动态端口区间。
        occupied.bind(("127.0.0.1", 8875))
        occupied.listen()
        requested_port = occupied.getsockname()[1]
        command = [str(executable)]
        if args.source:
            command.append(str(root / "desktop_launcher.py"))
        command += ["--data-dir", str(data_dir), "--port", str(requested_port), "--no-browser"]
        process = subprocess.Popen(command, cwd=data_dir, stdout=log, stderr=log)
        try:
            instance_path = data_dir / ".desktop-instance.json"
            deadline = time.monotonic() + 90
            while not instance_path.exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError(f"服务未启动，日志：{data_dir / 'verification.log'}")
                time.sleep(.2)
            url = json.loads(instance_path.read_text(encoding="utf-8"))["url"]
            assert f":{requested_port}/" not in url, "没有避让已占用端口"
            for path, expected in (("", "text/html"), ("static/css/workspace.css", "text/css"),
                                   ("static/js/reminders.js", "javascript"),
                                   ("static/vendor/chart.umd.min.js", "javascript"),
                                   ("static/images/logo.svg", "svg")):
                with urllib.request.urlopen(url + path, timeout=15) as response:
                    assert response.status == 200
                    assert expected in response.headers.get("Content-Type", ""), path
                    assert response.read(), path
            verify_user_flow(url)
            duplicate = subprocess.run(command, cwd=data_dir, capture_output=True, timeout=45)
            assert duplicate.returncode == 0, duplicate.stderr.decode("utf-8", errors="replace")
            assert "已在运行" in duplicate.stdout.decode("utf-8", errors="replace")
            print(f"DESKTOP_HTTP_OK: assets, registration, login, task create/complete, math, health, logout, occupied port fallback, single instance; {data_dir}")
        finally:
            process.terminate()
            process.wait(timeout=15)


if __name__ == "__main__":
    main()
