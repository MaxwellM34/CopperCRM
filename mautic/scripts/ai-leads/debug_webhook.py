#!/usr/bin/env python3
"""
Minimal webhook echo for debugging Mautic payloads.
"""
import json
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()  # allow sharing .env with other scripts

app = Flask(__name__)


@app.route("/debug/webhook", methods=["POST"])
def debugWebhook():
    try:
        payload = request.get_json(force=True, silent=True)
        raw_body = request.get_data(as_text=True)
        headers = dict(request.headers)

        app.logger.info("Headers: %s", headers)
        app.logger.info("JSON payload: %s", json.dumps(payload, indent=2) if payload is not None else "None")
        app.logger.info("Raw body: %s", raw_body)
        # Also print to stdout so you can see it directly in the terminal
        print("==== DEBUG WEBHOOK ====")
        print("Headers:", headers)
        print("JSON:", json.dumps(payload, indent=2) if payload is not None else "None")
        print("Raw:", raw_body)
        print("=======================")

        return jsonify(
            {
                "ok": True,
                "received_json": payload,
                "received_raw": raw_body,
                "received_headers": headers,
            }
        )
    except Exception as e:  # pragma: no cover - debug only
        app.logger.exception("debug_webhook failed")
        return jsonify({"ok": False, "error": str(e)}), 500


def runServer():
    port = int(os.getenv("DEBUG_WEBHOOK_PORT", "5002"))
    host = os.getenv("DEBUG_WEBHOOK_HOST", "0.0.0.0")
    app.run(host=host, port=port)


if __name__ == "__main__":
    runServer()
