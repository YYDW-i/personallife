# 用 PyInstaller 构建包含 Python、Django、CPU 训练运行时的目录发行包。
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

root = Path(SPECPATH)
apps = ['config', 'accounts', 'core', 'tasks', 'planner', 'maths', 'news',
        'analytics_app', 'profiles', 'players', 'deeplearning']
hidden = []
datas = [(str(root / 'templates'), 'templates'), (str(root / 'static'), 'static'),
         (str(root / 'analytics_app' / 'data'), 'analytics_app/data'),
         (str(root / 'LICENSE'), '.')]
for app in apps:
    hidden += collect_submodules(app)
datas += collect_data_files('sklearn')
datas += collect_data_files('lunar_python')
datas += collect_data_files('tzdata')

a = Analysis(['desktop_launcher.py'], pathex=[str(root)], binaries=[], datas=datas,
             hiddenimports=hidden, hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['torchaudio', 'IPython', 'pytest', 'tensorboard', 'tkinter', '__main__'])
# Django 的默认打包 hook 会自动夹带 manage.py 同级数据库，发行包必须明确排除。
def is_runtime_data(entry):
    destination = Path(entry[0])
    source = Path(entry[1])
    name = destination.name.lower()
    return (name == '.secret_key' or name.startswith('.env')
            or name.endswith(('.db', '.sqlite', '.sqlite3', '.sqlite3-wal', '.sqlite3-shm', '.sqlite3-journal'))
            or (source.parent == root and name.startswith('db.'))
            or any(part.lower() in {'media', 'userdata', 'backups'} for part in destination.parts))

a.datas = [entry for entry in a.datas if not is_runtime_data(entry)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='LocalLife',
          debug=False, strip=False, upx=False, console=True, version='packaging/version_info.txt',
          icon='packaging/locallife.ico')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='LocalLife')
