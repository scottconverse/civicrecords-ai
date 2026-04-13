"""Central LLM generation client.

All LLM generation calls route through this module to ensure:
1. Context manager budgeting (assemble_context / blocks_to_prompt)
2. Prompt injection sanitization (sanitize_for_llm)
3. Consistent Ollama API interaction
4. Centralized error handling and logging
"""

import logging
from typing import Any

import httpx

from app.config import settings
from app.llm.context_manager import (
    assemble_context,
    blocks_to_prompt,
    get_active_model_context_window,
    sanitize_for_llm,
)

logger = logging.getLogger(__name__)

_OLLAMA_TIMEOUT = 120.0


async def generate(
    *,
    system_prompt: str,
    user_content: str,
    model: str | None = None,
    chunks: list[str] | None = None,
    exemption_rules: list[str] | None = None,
    images: list[str] | None = None,
    timeout: float = _OLLAMA_TIMEOUT,
) -> str:
    """Generate text via Ollama with context management and sanitization.

    Args:
        system_prompt: The system instruction for the LLM.
        user_content: The primary user/request content (sanitized automatically).
        model: Ollama model name. Defaults to settings.chat_model.
        chunks: Optional document chunks (sanitized via assemble_context).
        exemption_rules: Optional exemption rules (sanitized via assemble_context).
        images: Optional base64-encoded images for multimodal models.
        timeout: Request timeout in seconds.

    Returns:
        The LLM's response text.

    Raises:
        RuntimeError: If the Ollama API returns a non-200 status.
    """
    resolved_model = model or settings.chat_model

    # Get active model context window for budget scaling
    max_ctx = await get_active_model_context_window()

    # Assemble context with token budgeting and sanitization
    blocks = assemble_context(
        system_prompt=system_prompt,
        request_context=sanitize_for_llm(user_content),
        chunks=chunks,
        exemption_rules=exemption_rules,
        max_context_tokens=max_ctx,
    )
    prompt = blocks_to_prompt(blocks)

    # Build Ollama payload
    payload: dict[str, Any] = {
        "model": resolved_model,
        "prompt": prompt,
        "stream": False,
    }
    if images:
        payload["images"] = images

    logger.info(
        "LLM generate: model=%s tokens_est=%d chunks=%d rules=%d",
        resolved_model,
        sum(b.estimated_tokens for b in blocks),
        len(chunks or []),
        len(exemption_rules or []),
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json=payload,
        )

    if resp.status_code != 200:
        error_detail = resp.text[:500]
        logger.error(
            "Ollama API error: status=%d model=%s detail=%s",
            resp.status_code,
            resolved_model,
            error_detail,
        )
        raise RuntimeError(
            f"Ollama generation failed (status {resp.status_code}): {error_detail}"
        )

    result = resp.json().get("response", "")
    logger.debug("LLM response length: %d chars", len(result))
    return result
