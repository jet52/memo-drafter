"""Wrap Anthropic SDK with retry logic and token tracking."""

import asyncio
import logging
import time

import anthropic

logger = logging.getLogger(__name__)

# Cost per million tokens (Sonnet 4 pricing)
INPUT_COST_PER_M = 3.00
OUTPUT_COST_PER_M = 15.00


class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
    ) -> str:
        """Generate a response with automatic retry on rate limits."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.client.messages.create,
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                self.total_input_tokens += response.usage.input_tokens
                self.total_output_tokens += response.usage.output_tokens
                logger.debug(
                    "API call: %d input, %d output tokens",
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                )
                return response.content[0].text

            except anthropic.RateLimitError:
                wait = 4 * (2 ** attempt)
                logger.warning("Rate limited, waiting %ds (attempt %d/%d)", wait, attempt + 1, max_retries)
                await asyncio.sleep(wait)
            except anthropic.APIConnectionError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning("Connection error: %s, retrying...", e)
                await asyncio.sleep(2)

        raise RuntimeError("Max retries exceeded for Claude API call")

    def estimate_cost(self) -> float:
        """Estimate cost based on token usage so far."""
        input_cost = (self.total_input_tokens / 1_000_000) * INPUT_COST_PER_M
        output_cost = (self.total_output_tokens / 1_000_000) * OUTPUT_COST_PER_M
        return input_cost + output_cost

    def usage_summary(self) -> str:
        """Return a formatted usage summary."""
        cost = self.estimate_cost()
        return (
            f"Tokens: {self.total_input_tokens:,} input, {self.total_output_tokens:,} output | "
            f"Est. cost: ${cost:.4f}"
        )
