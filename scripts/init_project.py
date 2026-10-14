"""跨平台创建项目目录与包初始化文件。

用法（在项目根目录执行）:
    python scripts/init_project.py
"""
from pathlib import Path


DIRS = [
    "app/api/v1/endpoints",
    "app/core",
    "app/db/models",
    "app/schemas",
    "app/services",
    "app/utils",
    "app/rag/retrievers",
    "app/rag/chains",
    "app/rag/pipeline",
    "app/rag/evaluation",
    "data/raw",
    "data/processed",
    "data/chroma",
    "data/eval/results",
    "scripts",
    "tests/test_api",
    "tests/test_rag",
    "tests/test_eval",
    "docker",
]

INIT_FILES = [
    "app/__init__.py",
    "app/api/__init__.py",
    "app/api/v1/__init__.py",
    "app/api/v1/endpoints/__init__.py",
    "app/core/__init__.py",
    "app/db/__init__.py",
    "app/db/models/__init__.py",
    "app/schemas/__init__.py",
    "app/services/__init__.py",
    "app/utils/__init__.py",
    "app/rag/__init__.py",
    "app/rag/retrievers/__init__.py",
    "app/rag/chains/__init__.py",
    "app/rag/pipeline/__init__.py",
    "app/rag/evaluation/__init__.py",
    "scripts/__init__.py",
    "tests/__init__.py",
]

# 保留空目录（git 不追踪空目录）
GITKEEP_FILES = [
    "data/raw/.gitkeep",
    "data/processed/.gitkeep",
    "data/chroma/.gitkeep",
    "data/eval/results/.gitkeep",
]


def main() -> None:
    root = Path.cwd()
    print(f"工作目录: {root}")

    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
        print(f"  [dir ] {d}")

    for f in INIT_FILES + GITKEEP_FILES:
        p = root / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch(exist_ok=True)
        print(f"  [file] {f}")

    print("\n✅ 目录初始化完成")


if __name__ == "__main__":
    main()