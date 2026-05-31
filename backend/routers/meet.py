from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from config import settings
from services.amap.recommendation import recommend_meeting_places
from services.asr_storage import save_asr_result
from services.audio_storage import save_audio_file
from services.bailian.asr import transcribe_audio_file
from services.bailian.tts import synthesize_speech
from services.deepseek.answer_generator import generate_meet_answer
from services.deepseek.slot_extractor import extract_location_slots
from utils import get_logger

router = APIRouter(prefix="/api/meet", tags=["meet"])
logger = get_logger()


@router.post("/voice")
async def meet_voice(audio: UploadFile = File(...)):
    logger.info("[语音接口] 收到上传 | filename=%s type=%s", audio.filename, audio.content_type)

    pipeline = settings.pipeline_status()
    if not pipeline["ready"]:
        missing = "、".join(pipeline["missing"])
        logger.error("[语音接口] 链路未就绪 | 缺少: %s", missing)
        raise HTTPException(
            status_code=503,
            detail=f"服务链路未就绪，请在 .env 中配置: {missing}",
        )

    saved = await save_audio_file(
        audio,
        settings.storage_path,
        max_size_bytes=settings.max_upload_size_bytes,
    )
    stem = Path(saved["filename"]).stem
    logger.info("[语音接口] 音频已保存 | path=%s", saved["storage_path"])

    asr_result = await transcribe_audio_file(
        Path(saved["absolute_path"]),
        saved.get("content_type"),
    )
    asr_saved = save_asr_result(
        settings.storage_path,
        saved["filename"],
        transcript=asr_result["transcript"],
        raw_response=asr_result["raw_response"],
    )
    transcript = asr_result["transcript"]
    logger.info("[语音接口] ASR 完成 | transcript=%s", transcript[:120] if transcript else "(空)")

    slot_result = await extract_location_slots(
        transcript,
        storage_dir=settings.storage_path,
        stem=stem,
    )
    slots = slot_result["slots"]

    meet_result = await recommend_meeting_places(
        slots,
        storage_dir=settings.storage_path,
        stem=stem,
    )
    recommendations = meet_result["recommendations"]
    logger.info("[语音接口] 高德MCP 完成 | 推荐数=%s", len(recommendations))

    answer_result = await generate_meet_answer(
        transcript=transcript,
        slots=slots,
        recommendations=recommendations,
        storage_dir=settings.storage_path,
        stem=stem,
    )
    answer = answer_result["answer"]

    tts_result = await synthesize_speech(
        answer,
        storage_dir=settings.storage_path,
        stem=stem,
    )
    logger.info("[语音接口] 全流程完成 | 回答=%s字 TTS=%s", len(answer), tts_result["audio_file"]["storage_path"])

    return {
        "saved": True,
        "audio": saved,
        "asr": asr_saved,
        "slots_artifact": slot_result["artifact"],
        "mcp_artifact": meet_result["artifact"],
        "answer_artifact": answer_result["artifact"],
        "tts_artifact": tts_result["artifact"],
        "transcript": transcript,
        "slots": slots,
        "recommendations": recommendations,
        "answer": answer,
        "audioBase64": tts_result["audioBase64"],
        "audioContentType": tts_result["audioContentType"],
        "audioUrl": tts_result.get("audioUrl"),
        "tts_audio": tts_result["audio_file"],
    }
