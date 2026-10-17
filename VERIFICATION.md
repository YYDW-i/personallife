# LocalLife 2.0.1 验收记录

日期：2026-10-17。环境：Windows 11 x64、Python 3.12.14、Django 5.2.18、PyTorch 2.7.1 CPU。

## 已通过的检查

| 检查 | 结果 |
| --- | --- |
| Django 系统检查 | 无问题 |
| 数据库模型与迁移一致性 | 无待生成迁移 |
| 自动回归测试 | 56 项全部通过（本次新增 20 项易经 AI 测试） |
| 离线数据集与模型实际训练 | 5 种数据集 × 3 种模型，共 15 组通过 |
| 导出代码 | 7 种数据集 × 3 种模型的语法检查通过；自定义回归与随机分类代码真实执行通过 |
| 易经 AI 真实接口 | 配置的 glm-4-flash-250414 返回有效解读，约 7.2 秒；译文 224 字、建议 3 条、文化背景 1 条 |
| 易经异常与重试 | 模拟原报错中的萃卦 / 恒卦嵌套译文、截断后自动重试、持续失败后手动重试、同卦象凭证保持、HTML 转义与权限检查通过 |
| 本次浏览器验收 | 新版易经页面、AI 译文与问题回应、重试入口、390px 布局无横向溢出；控制台无错误；Iris + MLP 30 轮真实训练完成 |
| README | 10 张新版真实页面截图；本地资源引用检查通过，AI 与新闻展示样本明确标注 |
| 浏览器交互 | 求导、常数作图、训练完成与曲线、移动导航、数学页面接收任务提醒通过 |
| 响应式布局 | 1440px 桌面与 390px 手机视口检查通过，无页面横向溢出 |
| EXE 自检 | 10 个主页面、符号计算、常数绘图及真实 CPU 训练通过 |
| EXE 实际 HTTP 流程 | 注册登录、创建与完成任务、数学 API、健康资料保存、起卦与 AI 缺少密钥提示及重试入口、退出登录通过 |
| 启动兼容性 | 静态资源、端口避让和重复启动复用实例通过 |
| 发行包一致性 | 126 个项目模块与 33 个页面/静态资源同源码一致 |
| 数据排除 | 发行目录不含个人数据库、.env 和 .secret_key |

上述功能测试使用专用 `.runtime-*` 数据目录或 Django 测试数据库，没有将原项目个人数据库作为测试库。

## 验收命令

```powershell
.\.venv-desktop\Scripts\python.exe manage.py check
.\.venv-desktop\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv-desktop\Scripts\python.exe manage.py test
.\.venv-desktop\Scripts\python.exe scripts\verify_training.py
.\dist\LocalLife-2.0.1\LocalLife.exe --smoke-test --data-dir .runtime-new-package-check --no-browser
.\.venv-desktop\Scripts\python.exe scripts\verify_desktop.py dist\LocalLife-2.0.1\LocalLife.exe
.\.venv-desktop\Scripts\python.exe scripts\verify_package_sources.py dist\LocalLife-2.0.1\LocalLife.exe
```

自检目录必须没有现存数据库；每次运行可更换目录名。HTTP 验收会占用 8875 端口，检查启动器自动选择其他端口，并在结束后停止测试进程。

## 实际使用边界

- 新闻抓取使用受控 RSS 样本进行回归验证，外部新闻源的实时可用性取决于网络和源站。
- 易经 AI 使用项目已配置的智谱模型完成一次真实接口测试，问题为不含个人资料的阅读习惯示例；截断、结构变体、错误分支和浏览器展示通过受控模拟响应验证。健康 AI 与外部新闻摘要后端未在本次追加真实调用。外部服务的持续可用性仍取决于网络、额度和模型权限。
- MNIST/FashionMNIST 在线下载未在本次验收中执行；其生成代码通过语法检查。发行包默认 CPU 训练。
- 提醒需要服务与浏览器运行；提示音需用户手势解锁，系统通知需浏览器授权。
- 这份验收记录覆盖本次确认的缺陷和关键使用流程，不能保证软件不存在其他缺陷。

## 本次发行目录

新版为 `dist/LocalLife-2.0.1/LocalLife.exe`，Windows 文件版本与产品版本均为 2.0.1。检测到旧版实例仍在使用 `dist/LocalLife`，本次构建改用独立目录，未停止该会话。使用新版前先关闭旧版启动窗口；保留同一数据目录即可沿用原资料。新目录的冻结包自检、实际 HTTP 流程、源码一致性与隐私文件排除检查均通过。
