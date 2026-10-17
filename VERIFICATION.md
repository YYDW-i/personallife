# LocalLife 2.0.0 验收记录

日期：2026-10-17。环境：Windows 11 x64、Python 3.12.14、Django 5.2.18、PyTorch 2.7.1 CPU。

## 已通过的检查

| 检查 | 结果 |
| --- | --- |
| Django 系统检查 | 无问题 |
| 数据库模型与迁移一致性 | 无待生成迁移 |
| 自动回归测试 | 36 项全部通过 |
| 离线数据集与模型实际训练 | 5 种数据集 × 3 种模型，共 15 组通过 |
| 导出代码 | 7 种数据集 × 3 种模型的语法检查通过；自定义回归与随机分类代码真实执行通过 |
| 浏览器交互 | 求导、常数作图、训练完成与曲线、移动导航、数学页面接收任务提醒通过 |
| 响应式布局 | 1440px 桌面与 390px 手机视口检查通过，无页面横向溢出 |
| EXE 自检 | 10 个主页面、符号计算、常数绘图及真实 CPU 训练通过 |
| EXE 实际 HTTP 流程 | 注册登录、创建与完成任务、数学 API、健康资料保存、退出登录通过 |
| 启动兼容性 | 静态资源、端口避让和重复启动复用实例通过 |
| 发行包一致性 | 126 个项目模块与 30 个页面/静态资源同源码一致 |
| 数据排除 | 发行目录不含个人数据库、.env 和 .secret_key |

上述功能测试使用专用 `.runtime-*` 数据目录或 Django 测试数据库，没有将原项目个人数据库作为测试库。

## 验收命令

```powershell
.\.venv-desktop\Scripts\python.exe manage.py check
.\.venv-desktop\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv-desktop\Scripts\python.exe manage.py test
.\.venv-desktop\Scripts\python.exe scripts\verify_training.py
.\dist\LocalLife\LocalLife.exe --smoke-test --data-dir .runtime-new-package-check --no-browser
.\.venv-desktop\Scripts\python.exe scripts\verify_desktop.py dist\LocalLife\LocalLife.exe
.\.venv-desktop\Scripts\python.exe scripts\verify_package_sources.py dist\LocalLife\LocalLife.exe
```

自检目录必须没有现存数据库；每次运行可更换目录名。HTTP 验收会占用 8875 端口，检查启动器自动选择其他端口，并在结束后停止测试进程。

## 实际使用边界

- 新闻抓取使用受控 RSS 样本进行回归验证，外部新闻源的实时可用性取决于网络和源站。
- 本次没有发出真实 AI 请求；AI 成功、失败、缓存和主动触发流程通过模拟客户端验证。使用时需配置有效智谱密钥。
- MNIST/FashionMNIST 在线下载未在本次验收中执行；其生成代码通过语法检查。发行包默认 CPU 训练。
- 提醒需要服务与浏览器运行；提示音需用户手势解锁，系统通知需浏览器授权。
- 这份验收记录覆盖本次确认的缺陷和关键使用流程，不能保证软件不存在其他缺陷。
