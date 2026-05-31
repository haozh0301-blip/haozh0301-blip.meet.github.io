import json
from pathlib import Path


def save_asr_result(
    storage_dir: Path,
    audio_filename: str,
    *,
    transcript: str,
    raw_response: dict,
) -> dict:
    storage_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(audio_filename).stem
    json_name = f"{stem}_asr.json"
    txt_name = f"{stem}_asr.txt"

    json_path = storage_dir / json_name
    txt_path = storage_dir / txt_name

    json_path.write_text(
        json.dumps(raw_response, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    txt_path.write_text(transcript, encoding="utf-8")

    storage_prefix = storage_dir.name

    return {
        "asr_json": {
            "filename": json_name,
            "storage_path": f"{storage_prefix}/{json_name}",
            "absolute_path": str(json_path),
        },
        "asr_txt": {
            "filename": txt_name,
            "storage_path": f"{storage_prefix}/{txt_name}",
            "absolute_path": str(txt_path),
        },
    }
