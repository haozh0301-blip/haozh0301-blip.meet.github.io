import json
from typing import Any

from config import settings
from services.deepseek.client import chat_completion
from utils import get_logger, preview_data, save_json_artifact, utc_now_iso

logger = get_logger()

ANSWER_SYSTEM_PROMPT = """你是 Meet 碰面助手。根据用户语音、两人位置和高德地图推荐结果，生成简洁、口语化的中文回答，适合语音播报。

要求：
1. 用自然口吻，先确认用户和朋友各自在哪
2. 介绍 1~3 个推荐碰面地点，说明名称、地址，以及双方路程/时间（如有）
3. 给出首选推荐并简要说明理由
4. 不要使用 markdown、列表符号或 JSON
5. 控制在 300 字以内"""


async def generate_meet_answer(
    *,
    transcript: str,
    slots: dict[str, dict[str, str]],
    recommendations: list[dict[str, Any]],
    storage_dir,
    stem: str,
) -> dict[str, Any]:
    logger.info("[回答生成] 开始 | 推荐数=%s", len(recommendations))

    context = {
        "transcript": transcript,
        "slots": slots,
        "recommendations": recommendations,
    }

    payload = {
        "model": settings.deepseek_answer_model,
        "messages": [
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "请根据以下信息生成碰面推荐回答：\n"
                    f"{json.dumps(context, ensure_ascii=False, indent=2)}"
                ),
            },
        ],
        "thinking": {"type": "disabled"},
        "temperature": settings.deepseek_answer_temperature,
        "max_tokens": settings.deepseek_answer_max_tokens,
        "stream": False,
    }

    raw_response = await chat_completion(payload)
    choices = raw_response.get("choices") or []
    answer = ""
    if choices:
        answer = ((choices[0].get("message") or {}).get("content") or "").strip()

    artifact = {
        "started_at": utc_now_iso(),
        "input": context,
        "request_payload": {
            "model": settings.deepseek_answer_model,
            "temperature": settings.deepseek_answer_temperature,
        },
        "raw_response": raw_response,
        "answer": answer,
        "finished_at": utc_now_iso(),
    }
    saved = save_json_artifact(storage_dir, stem, "answer", artifact)

    logger.info("[回答生成] 完成 | 长度=%s | 留档=%s", len(answer), saved["storage_path"])
    logger.info("[回答生成] 预览 | %s", preview_data(answer, 160))

    return {"answer": answer, "raw_response": raw_response, "artifact": saved}
