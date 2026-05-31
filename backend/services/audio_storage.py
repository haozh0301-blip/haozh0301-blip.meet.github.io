import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

CONTENT_TYPE_EXTENSION = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
}


def _resolve_extension(upload_file: UploadFile) -> str:
    if upload_file.filename and "." in upload_file.filename:
        suffix = Path(upload_file.filename).suffix.lower()
        if suffix:
            return suffix

    content_type = (upload_file.content_type or "").split(";")[0].strip().lower()
    return CONTENT_TYPE_EXTENSION.get(content_type, ".bin")


async def save_audio_file(
    upload_file: UploadFile,
    storage_dir: Path,
    *,
    max_size_bytes: int,
) -> dict:
    if not upload_file.content_type or not upload_file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="仅支持上传音频文件")

    storage_dir.mkdir(parents=True, exist_ok=True)

    extension = _resolve_extension(upload_file)
    filename = f"{uuid.uuid4().hex}{extension}"
    file_path = storage_dir / filename

    content = await upload_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="音频文件为空")

    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"音频文件过大，最大允许 {max_size_bytes // (1024 * 1024)}MB",
        )

    file_path.write_bytes(content)

    return {
        "filename": filename,
        "storage_path": f"{storage_dir.name}/{filename}",
        "absolute_path": str(file_path),
        "size_bytes": len(content),
        "content_type": upload_file.content_type,
    }
