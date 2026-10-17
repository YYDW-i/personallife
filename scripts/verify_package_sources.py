"""比对 EXE 中的项目字节码，防止长时间构建中途编辑代码导致发行包落后。"""
import argparse
import marshal
from pathlib import Path
import types

from PyInstaller.archive.readers import CArchiveReader


def signature(code):
    return (code.co_code, code.co_names, code.co_varnames, code.co_freevars,
            code.co_cellvars, code.co_argcount, code.co_kwonlyargcount, code.co_flags,
            tuple(signature(value) if isinstance(value, types.CodeType) else value
                  for value in code.co_consts))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    reader = CArchiveReader(str(args.executable))
    archive = reader.open_embedded_archive("PYZ.pyz")
    mismatches = []
    checked = 0
    for app in ("config", "core", "tasks", "planner", "accounts", "profiles", "players",
                "news", "maths", "analytics_app", "deeplearning"):
        for source in (root / app).rglob("*.py"):
            module = ".".join(source.relative_to(root).with_suffix("").parts)
            if module.endswith(".__init__"):
                module = module[:-9]
            if module not in archive.toc:
                continue
            actual = archive.extract(module)
            expected = compile(source.read_text(encoding="utf-8-sig"), str(source), "exec")
            checked += 1
            if signature(actual) != signature(expected):
                mismatches.append(module)
    source = root / "desktop_launcher.py"
    actual = marshal.loads(reader.extract("desktop_launcher"))
    if signature(actual) != signature(compile(source.read_text(encoding="utf-8"), str(source), "exec")):
        mismatches.append("desktop_launcher")
    if mismatches:
        raise RuntimeError(f"构建期间源代码发生变化，请重新构建：{', '.join(mismatches)}")
    resources = 0
    bundle = args.executable.resolve().parent
    for directory in ("templates", "static"):
        for source in (root / directory).rglob("*"):
            if not source.is_file():
                continue
            target = bundle / "_internal" / source.relative_to(root)
            if not target.is_file() or target.read_bytes() != source.read_bytes():
                raise RuntimeError(f"发行包资源缺失或过期：{source.relative_to(root)}")
            resources += 1
    for path in bundle.rglob("*"):
        if path.name in {".env", ".secret_key", "db.sqlite3"}:
            raise RuntimeError(f"发行包意外包含运行时数据：{path}")
    print(f"PACKAGE_SOURCES_OK: {checked + 1} modules, {resources} resources match workspace; no personal database or keys")


if __name__ == "__main__":
    main()
