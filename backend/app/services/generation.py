import json
from typing import AsyncGenerator, List
import httpx
from app.config import settings
from app.schemas.chat import RetrievedChunk
from app.models.message import Message
import structlog

logger = structlog.get_logger()

async def stream_answer(
    question: str,
    retrieved_chunks: List[RetrievedChunk],
    chat_history: List[Message],
    max_history_turns: int = 6,
) -> AsyncGenerator[str, None]:
    """
    1. Build context string from retrieved_chunks (truncate at MAX_CONTEXT_TOKENS)
    2. Build system prompt
    3. Build messages list: system + last N history turns + current question with context
    4. POST to vLLM /v1/chat/completions with stream=True
    5. Parse SSE delta chunks and yield token strings
    6. On finish, yield a special sentinel JSON with sources metadata
    """
    
    
    if settings.MOCK_VLLM:
        logger.info("generating_mock_streaming_answer")
        import asyncio
        if retrieved_chunks:
            answer = (
                f"Based on the provided document contexts, here is what I found:\n\n"
                f"- A chunk from **{retrieved_chunks[0].filename}** on page {retrieved_chunks[0].source_page} states: "
                f"\"{retrieved_chunks[0].text[:120]}...\" [Source 1]\n"
            )
            if len(retrieved_chunks) > 1:
                answer += f"- Another passage from **{retrieved_chunks[1].filename}** (page {retrieved_chunks[1].source_page}) indicates: \"{retrieved_chunks[1].text[:120]}...\" [Source 2]\n"
            answer += "\nIs there anything specific you would like me to elaborate on?"
        else:
            answer = "I couldn't find relevant information in the uploaded documents to answer that."

        for word in answer.split(" "):
            yield word + " "
            await asyncio.sleep(0.03) # simulate token streaming latency
            
        sources_metadata = [
            {
                "id": chunk.id,
                "filename": chunk.filename,
                "source_page": chunk.source_page,
                "text": chunk.text,
                "score": chunk.score
            }
            for chunk in retrieved_chunks
        ]
        yield f"[SOURCES_METADATA]{json.dumps(sources_metadata)}"
        return

    # 1. Build context string and truncate based on character approximation of MAX_CONTEXT_TOKENS
    # (Approx. 4 characters per token)
    max_context_chars = settings.MAX_CONTEXT_TOKENS * 4
    context_parts = []
    current_chars = 0

    for i, chunk in enumerate(retrieved_chunks, 1):
        passage = (
            f"[Source {i}] (from: {chunk.filename}, page {chunk.source_page})\n"
            f"---\n"
            f"{chunk.text}\n"
            f"---\n\n"
        )
        if current_chars + len(passage) > max_context_chars:
            break
        context_parts.append(passage)
        current_chars += len(passage)

    context_str = "".join(context_parts) if context_parts else "No context passages available."

    # 2. Build system prompt
    system_prompt = (
        "You are a precise question-answering assistant. Answer the user's question using ONLY "
        "the context passages provided below. Follow these rules strictly:\n\n"
        "RULES:\n"
        "1. Base your answer exclusively on the provided context. Do not use external knowledge.\n"
        "2. If the context does not contain enough information to answer, say:\n"
        "   \"I couldn't find relevant information in the uploaded documents to answer that.\"\n"
        "3. Cite your sources inline using [Source N] notation where N matches the passage number.\n"
        "4. Be concise and direct. Prefer bullet points for multi-part answers.\n"
        "5. Never fabricate facts, statistics, or quotations not present in the context.\n"
        "6. Maintain a professional, neutral tone."
    )

    # 3. Build messages list
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Add last N message turns from history
    # max_history_turns defaults to 6 messages (3 user-assistant exchanges)
    history_to_include = chat_history[-max_history_turns:] if chat_history else []
    for msg in history_to_include:
        messages.append({
            "role": msg.role,
            "content": msg.content
        })

    # Add current question with context
    current_user_content = (
        f"CONTEXT PASSAGES:\n"
        f"{context_str}\n"
        f"USER QUESTION:\n"
        f"{question}"
    )
    messages.append({
        "role": "user",
        "content": current_user_content
    })

    # 4. POST to vLLM
    url = f"{settings.VLLM_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    if settings.HF_TOKEN and settings.HF_TOKEN != "hf_placeholder":
        headers["Authorization"] = f"Bearer {settings.HF_TOKEN}"

    payload = {
        "model": settings.LLM_MODEL_NAME,
        "messages": messages,
        "stream": True,
        # Set temperature to 0 for exact facts QA
        "temperature": 0.0,
    }

    try:
        logger.info("requesting_vllm_streaming", url=url, model=settings.LLM_MODEL_NAME)
        
        async with httpx.AsyncClient(timeout=settings.STREAM_TIMEOUT) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error("vllm_generation_failed", status_code=response.status_code, error=error_text.decode())
                    yield f"[ERROR] vLLM returned status {response.status_code}"
                    return

                # 5. Parse SSE delta chunks and yield token strings
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            logger.warning("failed_to_decode_sse_chunk", line=line)
                            continue

    except Exception as e:
        logger.error("vllm_stream_exception", error=str(e))
        yield f"[ERROR] Generation stream encountered an error: {str(e)}"
        return

    # 6. On finish, yield special sentinel JSON with sources metadata
    sources_metadata = [
        {
            "id": chunk.id,
            "filename": chunk.filename,
            "source_page": chunk.source_page,
            "text": chunk.text,
            "score": chunk.score
        }
        for chunk in retrieved_chunks
    ]
    
    yield f"[SOURCES_METADATA]{json.dumps(sources_metadata)}"
