
import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMTelemetry(BaseModel):
    model: str
    prompt_version: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    cost_usd: float


class LLMResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    raw_content: str
    is_valid_schema: bool
    telemetry: LLMTelemetry
    error: Optional[str] = None


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        prompt_version: str = "1.0",
        system_instruction: Optional[str] = None,
    ) -> LLMResponse[T]:
        pass


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic provider for CI/CD and offline evaluation.
    Supports fault injection: simulation of timeouts, invalid JSON, or schema errors.
    """

    def __init__(
        self,
        default_responses: Optional[Dict[str, Any]] = None,
        simulate_timeout: bool = False,
        simulate_malformed_json: bool = False,
        cost_per_1k_tokens: float = 0.002,
    ):
        self.default_responses = default_responses or {}
        self.simulate_timeout = simulate_timeout
        self.simulate_malformed_json = simulate_malformed_json
        self.cost_per_1k_tokens = cost_per_1k_tokens

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        prompt_version: str = "1.0",
        system_instruction: Optional[str] = None,
    ) -> LLMResponse[T]:
        start = time.perf_counter()

        if self.simulate_timeout:
            await asyncio.sleep(0.5)
            raise TimeoutError("LLM generation timed out after 500ms")

        if self.simulate_malformed_json:
            raw = "{ invalid json: 123 "
            latency_ms = int((time.perf_counter() - start) * 1000)
            return LLMResponse(
                raw_content=raw,
                is_valid_schema=False,
                error="Invalid JSON output",
                telemetry=LLMTelemetry(
                    model="mock-deterministic",
                    prompt_version=prompt_version,
                    prompt_tokens=50,
                    completion_tokens=10,
                    latency_ms=latency_ms,
                    cost_usd=0.0001,
                ),
            )

        # Lookup in configured responses or build from default
        res_dict = self.default_responses.get(prompt)
        if not res_dict:
            # Fallback to model construct with defaults or first entry
            res_dict = self.default_responses.get("default", {})

        raw_str = json.dumps(res_dict)
        latency_ms = int((time.perf_counter() - start) * 1000)
        tokens = len(prompt.split()) + len(raw_str.split())
        cost = (tokens / 1000.0) * self.cost_per_1k_tokens

        try:
            parsed = response_model.model_validate(res_dict)
            return LLMResponse(
                data=parsed,
                raw_content=raw_str,
                is_valid_schema=True,
                telemetry=LLMTelemetry(
                    model="mock-deterministic",
                    prompt_version=prompt_version,
                    prompt_tokens=len(prompt.split()),
                    completion_tokens=len(raw_str.split()),
                    latency_ms=latency_ms,
                    cost_usd=round(cost, 6),
                ),
            )
        except Exception as e:
            return LLMResponse(
                data=None,
                raw_content=raw_str,
                is_valid_schema=False,
                error=f"Schema validation error: {str(e)}",
                telemetry=LLMTelemetry(
                    model="mock-deterministic",
                    prompt_version=prompt_version,
                    prompt_tokens=len(prompt.split()),
                    completion_tokens=len(raw_str.split()),
                    latency_ms=latency_ms,
                    cost_usd=round(cost, 6),
                ),
            )


class LLMClient:
    """
    Client orchestrating retries and timeout boundaries (FR-AI-001, TS-080).
    """

    def __init__(self, provider: BaseLLMProvider, max_retries: int = 2, timeout_seconds: float = 5.0):
        self.provider = provider
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

    async def call_with_retry(
        self,
        prompt: str,
        response_model: Type[T],
        prompt_version: str = "1.0",
        system_instruction: Optional[str] = None,
    ) -> LLMResponse[T]:
        attempts = 0
        last_error = None

        while attempts <= self.max_retries:
            attempts += 1
            try:
                resp = await asyncio.wait_for(
                    self.provider.generate_structured(
                        prompt=prompt,
                        response_model=response_model,
                        prompt_version=prompt_version,
                        system_instruction=system_instruction,
                    ),
                    timeout=self.timeout_seconds,
                )
                if resp.is_valid_schema:
                    return resp
                last_error = resp.error
            except (TimeoutError, asyncio.TimeoutError) as e:
                last_error = f"Timeout after {self.timeout_seconds}s"
            except Exception as e:
                last_error = str(e)

            # Exponential backoff between retries
            if attempts <= self.max_retries:
                await asyncio.sleep(0.05 * (2 ** (attempts - 1)))

        return LLMResponse(
            data=None,
            raw_content="",
            is_valid_schema=False,
            error=f"Exhausted retries ({self.max_retries + 1} attempts). Last error: {last_error}",
            telemetry=LLMTelemetry(
                model="unknown",
                prompt_version=prompt_version,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0,
                cost_usd=0.0,
            ),
        )
