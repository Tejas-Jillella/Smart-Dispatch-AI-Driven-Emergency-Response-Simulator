import json
import os
import re

import requests
from flask_cors import CORS
from flask import Flask, request, jsonify

app = Flask(__name__)
CORS(app)
GROK_API_KEY = os.environ.get("GROK_API_KEY")
GROK_MODEL = os.environ.get("GROK_MODEL", "grok-4")

SYSTEM_PROMPT = """
You are an emergency dispatch decision system for a smart city.

Rules:
- crime/robbery/theft/assault/violence → police
- fire/smoke/explosion → fire
- injury/medical/unconscious → medical
- multiple responders allowed

Return ONLY valid JSON:

{
  "responders": ["police" | "fire" | "medical"],
  "priority": "low" | "medium" | "high",
  "reason": "short explanation"
}
"""


def rule_based_dispatch(incident: str) -> dict:
    text = (incident or "").lower()
    has_fire = any(
        keyword in text for keyword in ["fire", "explosion"]
    )
    has_police = any(
        keyword in text for keyword in ["shooting", "murder", "attack"]
    )
    has_medical = any(
        keyword in text for keyword in ["injury", "injured", "medical"]
    )

    responders = []
    if has_fire:
        responders.append("fire")
    if has_police:
        responders.append("police")
    if has_medical:
        responders.append("medical")

    if not responders:
        return {
            "responders": ["police"],
            "priority": "low" if not text.strip() else "medium",
            "reason": "Fallback dispatch defaulted to police because no incident keywords matched.",
        }

    if has_fire or len(responders) > 1:
        priority = "high"
    elif has_medical:
        priority = "high"
    else:
        priority = "high" if any(keyword in text for keyword in ["assault", "violence", "weapon"]) else "medium"

    return {
        "responders": responders,
        "priority": priority,
        "reason": "Fallback dispatch selected responders from matched incident keywords in fire, police, medical priority order.",
    }


def call_grok_dispatch(incident: str) -> dict:
    if not GROK_API_KEY:
        raise RuntimeError("GROK_API_KEY is not set")

    response = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROK_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {"role": "user", "content": f"Incident: {incident}"},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "stream": False,
        },
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    text = data["choices"][0]["message"]["content"] or ""
    clean = re.sub(r"^```json\s*", "", text.strip(), flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean)
    parsed = json.loads(clean)

    responders = parsed.get("responders")
    priority = parsed.get("priority")
    reason = parsed.get("reason")
    valid_responders = {"police", "fire", "medical"}
    valid_priorities = {"low", "medium", "high"}

    if (
        not isinstance(responders, list)
        or not responders
        or any(responder not in valid_responders for responder in responders)
        or priority not in valid_priorities
        or not isinstance(reason, str)
        or not reason.strip()
    ):
        raise ValueError("Groq returned JSON that does not match the dispatch schema")

    return {
        "responders": responders,
        "priority": priority,
        "reason": reason.strip(),
    }

@app.route("/dispatch", methods=["POST", "OPTIONS"])
def dispatch():
    print("DISPATCH METHOD:", request.method)
    if request.method == "OPTIONS":
        return jsonify({"ok": True})

    payload_in = request.get_json() or {}
    incident = payload_in.get("incident", "")
    try:
        return jsonify(call_grok_dispatch(incident))
    except Exception as exc:
        print("Grok dispatch failed, using fallback:", exc)
        return jsonify(rule_based_dispatch(incident))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
