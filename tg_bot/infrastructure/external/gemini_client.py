from __future__ import annotations

import asyncio
from typing import Any, Optional

import google.generativeai as genai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.logger import get_logger

logger = get_logger(__name__)

_GENERATION_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 2048,
}

_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]


class GeminiClientError(Exception):
    pass


class GeminiTimeoutError(GeminiClientError):
    pass


class GeminiRateLimitError(GeminiClientError):
    pass


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        timeout: int = 30,
        model_name: str = "gemini-1.5-flash",
    ) -> None:
        self._max_retries = max_retries
        self._timeout = timeout
        self._model_name = model_name

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=_GENERATION_CONFIG,
            safety_settings=_SAFETY_SETTINGS,
        )

    async def generate(
        self,
        prompt: str,
        history: Optional[list[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        full_prompt = self._build_prompt(prompt, system_prompt)

        try:
            response_text = await asyncio.wait_for(
                self._generate_with_retry(full_prompt, history or []),
                timeout=self._timeout,
            )
            return response_text
        except asyncio.TimeoutError:
            logger.error("gemini.timeout", timeout=self._timeout)
            raise GeminiTimeoutError(f"Gemini timed out after {self._timeout}s")

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _generate_with_retry(
        self,
        prompt: str,
        history: list[dict],
    ) -> str:
        try:
            chat_history = [
                {"role": entry["role"], "parts": [entry["content"]]}
                for entry in history
            ]

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._model.start_chat(history=chat_history).send_message(prompt),
            )
            return response.text
        except Exception as exc:
            logger.warning("gemini.retry", error=str(exc))
            raise

    def _build_prompt(self, prompt: str, system_prompt: Optional[str]) -> str:
        if system_prompt:
            return f"{system_prompt}\n\n{prompt}"
        return prompt

    async def health_check(self) -> bool:
        try:
            response = await self.generate("ping", history=[])
            return bool(response)
        except Exception:
            return False
