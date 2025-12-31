#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI


# Default model for all scoring calls.
MODEL_NAME = "gpt-4.1-mini"


def _get_client() -> OpenAI:
    """
    Lazily construct an OpenAI client, ensuring the API key is present.

    This avoids importing / constructing a client in environments where the key
    is not configured, and gives a clear error message when missing.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set in the environment; "
            "cannot call the LLM scoring backend."
        )
    return OpenAI(api_key=api_key)


def call_llm(prompt: str, model: Optional[str] = None) -> str:
    """
    Call the LLM with a scoring prompt and return the raw JSON text response.

    The caller is responsible for constructing a prompt that:
      - fully defines the scoring rubric (1–7 or \"none\")
      - enforces strict JSON output
      - constrains the model to the desired dimension (value-prop, reaction, etc.)

    Behaviour:
      - Uses deterministic settings (temperature = 0).
      - Requests JSON-formatted output via response_format.
      - Raises RuntimeError with a clear message on any API error.

    Args:
        prompt: The full user prompt containing the scoring rubric.
        model:  Optional override for the model name. Defaults to MODEL_NAME.

    Returns:
        The raw JSON string returned by the model (message.content).

    Raises:
        RuntimeError: If the API key is missing, the API call fails, or the
                      response does not contain a message body.
    """
    client = _get_client()
    model_name = model or MODEL_NAME

    try:
        resp = client.chat.completions.create(
            model=model_name,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict scoring engine for cold email evaluation. "
                        "Follow the scoring rubric given in the user prompt EXACTLY "
                        "and respond only with a single JSON object."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
    except Exception as exc:
        raise RuntimeError(f"LLM scoring call failed: {exc}") from exc

    # Defensive check: ensure we have at least one choice with content.
    if not resp.choices or not resp.choices[0].message or resp.choices[0].message.content is None:
        raise RuntimeError("LLM scoring call returned no content in the response.")

    return resp.choices[0].message.content
