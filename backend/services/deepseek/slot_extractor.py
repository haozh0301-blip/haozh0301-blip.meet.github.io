import json
from typing import Any

from fastapi import HTTPException

from config import settings
from services.deepseek.client import chat_completion
from utils import get_logger, preview_data, save_json_artifact, utc_now_iso

logger = get_logger()

SLOT_SYSTEM_PROMPT = """你是位置信息提取助手。从用户语音转写文本中提取两人所在位置。
必须只输出 JSON，不要输出 markdown 或解释。

输出格式：
{
  "user": {"city": "城市名", "address": "具体地址或地标"},
  "friend": {"city": "城市名", "address": "具体地址或地标"}
}

规则：
1. city 和 address 都必须尽量填写；若只提到地标，address 填地标名，city 根据上下文推断。
2. 若无法区分两人，将第一个位置归为 user，第二个归为 friend。
3. 无法提取时对应字段填空字符串。
4. 地址尽量写完整名称，如「北京西站」而非「北京西」，「东方明珠广播电视塔」或「东方明珠」而非简称。"""


def _parse_slots(content: str) -> dict[str, dict[str, str]]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek 槽位 JSON 解析失败: {content[:200]}") from exc

    def normalize_person(key: str) -> dict[str, str]:
        person = data.get(key) or {}
        if not isinstance(person, dict):
            person = {}
        return {
            "city": str(person.get("city") or "").strip(),
            "address": str(person.get("address") or "").strip(),
        }

    return {"user": normalize_person("user"), "friend": normalize_person("friend")}


async def extract_location_slots(
    transcript: str,
    *,
    storage_dir,
    stem: str,
) -> dict[str, Any]:
    logger.info("[槽位提取] 开始 | 输入文本=%s", preview_data(transcript, 120))

    if not transcript.strip():
        raise HTTPException(status_code=400, detail="ASR 未识别到有效文本，无法进行槽位提取")

    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": SLOT_SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "temperature": settings.deepseek_temperature,
        "max_tokens": settings.deepseek_max_tokens,
        "stream": False,
    }

    raw_response = await chat_completion(payload)
    choices = raw_response.get("choices") or []
    content = ""
    if choices:
        content = (choices[0].get("message") or {}).get("content") or ""

    slots = _parse_slots(content)

    artifact = {
        "started_at": utc_now_iso(),
        "transcript": transcript,
        "request_payload": {
            "model": settings.deepseek_model,
            "temperature": settings.deepseek_temperature,
        },
        "raw_response": raw_response,
        "parsed_content": content,
        "slots": slots,
        "finished_at": utc_now_iso(),
    }
    saved = save_json_artifact(storage_dir, stem, "slots", artifact)

    logger.info(
        "[槽位提取] 完成 | user=%s/%s friend=%s/%s | 留档=%s",
        slots["user"]["city"],
        slots["user"]["address"],
        slots["friend"]["city"],
        slots["friend"]["address"],
        saved["storage_path"],
    )

    return {"slots": slots, "raw_response": raw_response, "artifact": saved}
