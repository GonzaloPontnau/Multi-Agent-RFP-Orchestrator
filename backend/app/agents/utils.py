"""Utilidades compartidas entre agentes."""

import json
import re


def parse_json_response(response: str) -> dict | None:
    """Parsea respuesta JSON del LLM, manejando posibles errores de formato."""
    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"```(?:json)?\n?", "", clean)
            clean = clean.rstrip("`")
        return json.loads(clean)
    except json.JSONDecodeError:
        return None
