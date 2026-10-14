"""文件相关辅助。"""
from pathlib import Path

from app.core.config import get_settings


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


def is_supported(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def save_upload(filename: str, content: bytes) -> Path:
    """保存上传文件到 data/raw/。"""
    settings = get_settings()
    safe_name = Path(filename).name
    target = settings.raw_dir / safe_name
    target.write_bytes(content)
    return target


def list_raw_files() -> list[Path]:
    settings = get_settings()
    return [
        p for p in settings.raw_dir.rglob("*")
        if p.is_file() and is_supported(p)
    ]