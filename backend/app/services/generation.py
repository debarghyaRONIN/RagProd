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
    
    
    # 1. Determine if the query is a simple greeting or general conversation
    is_conversational = False
    cleaned_query = question.strip().lower().rstrip('?.!')
    greetings = {
        "hi", "hello", "hey", "howdy", "greetings", "good morning", "good afternoon", "good evening",
        "thanks", "thank you", "thank you so much", "perfect", "ok", "okay", "bye", "goodbye",
        "who are you", "what is your name", "what can you do", "help", "who created you"
    }
    
    if cleaned_query in greetings or any(cleaned_query.startswith(g + " ") for g in ["hi", "hello", "hey", "thanks"]):
        is_conversational = True

    # Decide whether to run in RAG mode or Conversational mode
    use_rag = retrieved_chunks and not is_conversational

    if settings.MOCK_VLLM:
        logger.info("generating_mock_streaming_answer", use_rag=use_rag)
        import asyncio
        if use_rag:
            answer = (
                f"Based on the provided document contexts, here is what I found:\n\n"
                f"- A chunk from **{retrieved_chunks[0].filename}** on page {retrieved_chunks[0].source_page} states: "
                f"\"{retrieved_chunks[0].text[:120]}...\" [Source 1]\n"
            )
            if len(retrieved_chunks) > 1:
                answer += f"- Another passage from **{retrieved_chunks[1].filename}** (page {retrieved_chunks[1].source_page}) indicates: \"{retrieved_chunks[1].text[:120]}...\" [Source 2]\n"
            answer += "\nIs there anything specific you would like me to elaborate on?"
        else:
            if cleaned_query in {"hi", "hello", "hey", "howdy", "greetings"}:
                answer = "Hello! I am your RAG QA assistant. How can I help you today? You can chat with me generally or upload documents in the Library Workspace to query them."
            elif cleaned_query in {"thanks", "thank you", "thank you so much"}:
                answer = "You're very welcome! Let me know if there's anything else I can help you with."
            else:
                answer = (
                    f"I see you asked: \"{question}\". Since no document context is selected or available, "
                    f"I will answer from my general knowledge. Here is what I can tell you: this is a general chat "
                    f"response from the RAG QA Engine. Upload files to ground my responses in documents!"
                )

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
        ] if use_rag else []
        yield f"[SOURCES_METADATA]{json.dumps(sources_metadata)}"
        return

    # Build prompt configurations based on mode
    if use_rag:
        # Build context string and truncate based on character approximation of MAX_CONTEXT_TOKENS
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
        current_user_content = (
            f"CONTEXT PASSAGES:\n"
            f"{context_str}\n"
            f"USER QUESTION:\n"
            f"{question}"
        )
        temperature = 0.0
    else:
        # Conversational Mode (General chatbot fallback)
        system_prompt = (
            "You are a helpful, friendly, and highly intelligent AI assistant called RAG QA Engine. "
            "You are serving as a general chat assistant. Answer the user's question directly, clearly, "
            "and engage in normal conversation. Since the user has not selected any documents or no relevant "
            "document context was found, rely on your general knowledge to answer them. "
            "Maintain a friendly, professional tone. If the user asks about documents, politely remind them "
            "that they can upload files in the Document Library and select them to get context-grounded answers."
        )
        current_user_content = question
        temperature = 0.7

    # Build messages list
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Add last N message turns from history
    history_to_include = chat_history[-max_history_turns:] if chat_history else []
    for msg in history_to_include:
        messages.append({
            "role": msg.role,
            "content": msg.content
        })

    # Add current user prompt
    messages.append({
        "role": "user",
        "content": current_user_content
    })

    # POST to vLLM
    url = f"{settings.VLLM_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    if settings.HF_TOKEN:
        headers["Authorization"] = f"Bearer {settings.HF_TOKEN}"

    payload = {
        "model": settings.LLM_MODEL_NAME,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
    }

    try:
        logger.info("requesting_vllm_streaming", url=url, model=settings.LLM_MODEL_NAME, use_rag=use_rag)
        
        async with httpx.AsyncClient(timeout=settings.STREAM_TIMEOUT) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error("vllm_generation_failed", status_code=response.status_code, error=error_text.decode())
                    yield f"[ERROR] vLLM returned status {response.status_code}"
                    return

                # Parse SSE delta chunks and yield token strings
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

    # Yield sources metadata metadata array (empty if not RAG mode)
    sources_metadata = [
        {
            "id": chunk.id,
            "filename": chunk.filename,
            "source_page": chunk.source_page,
            "text": chunk.text,
            "score": chunk.score
        }
        for chunk in retrieved_chunks
    ] if use_rag else []
    
    yield f"[SOURCES_METADATA]{json.dumps(sources_metadata)}"

