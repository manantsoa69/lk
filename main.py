import asyncio
import json
import os
import sys
from pathlib import Path

import g4f
import requests
from dotenv import load_dotenv
from quart import Quart, jsonify, request

from gpt_chat import chat_with_gpt, update_provider_on_error

# Load environment variables from the .env file
load_dotenv()

app = Quart(__name__)

# You can access the environment variables like this
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")


@app.route("/")
async def home():
    print("Home endpoint reached")
    return {"message": "OK"}


@app.route("/webhook", methods=["GET", "POST"])
async def webhook():
    if request.method == "GET":
        verify_token = request.args.get("hub.verify_token")
        if verify_token == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        else:
            return "Invalid verification token", 403
    elif request.method == "POST":
        data = await request.get_json()
        if data["object"] == "page":
            for entry in data["entry"]:
                for messaging_event in entry["messaging"]:
                    sender_id = messaging_event["sender"]["id"]
                    recipient_id = messaging_event["recipient"]["id"]
                    if "message" in messaging_event:
                        message_text = messaging_event["message"]["text"]
                        print(f"User's question: {message_text}")
                        await handle_message(sender_id, message_text)
        return "OK"


async def send_message(sender_id, response_text):
    message_data = {"recipient": {"id": sender_id}, "message": {"text": response_text}}

    response = requests.post(
        f"https://graph.facebook.com/v13.0/me/messages?access_token={PAGE_ACCESS_TOKEN}",
        json=message_data,
    )

    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print("Failed to send message")


async def handle_message(sender_id, message_text):
    response_text = await chat_with_gpt(message_text)
    await send_message(sender_id, response_text)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
