import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )


def get_logger(name: str = "meet") -> logging.Logger:
    return logging.getLogger(name)


def save_json_artifact(storage_dir: Path, stem: str, suffix: str, data: Any) -> dict:
    storage_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{stem}_{suffix}.json"
    file_path = storage_dir / filename
    file_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    prefix = storage_dir.name
    return {
        "filename": filename,
        "storage_path": f"{prefix}/{filename}",
        "absolute_path": str(file_path),
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def preview_data(data: Any, max_len: int = 800) -> str:
    text = json.dumps(data, ensure_ascii=False, default=str)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "...(truncated)"
