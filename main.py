import asyncio
import json
import os
import sys
from pathlib import Path

import g4f
import requests
from dotenv import load_dotenv
from quart import Quart, jsonify, request, abort

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
@app.post("/update_provider")
async def update_provider():
    try:
        await update_provider_on_error()
        return {"message": "Provider updated successfully"}
    except Exception as e:
        raise abort(500, f"Error updating provider: {str(e)}")
      
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
                    print(sender_id)
                    recipient_id = messaging_event["recipient"]["id"]
                    if "message" in messaging_event:
                        message_text = messaging_event["message"]["text"]
                       
                        await handle_message(sender_id, message_text)
        return "OK"

async def send_message(sender_id, response_text):
    if len(response_text) > 2000:
        chunks = [response_text[i:i + 2000] for i in range(0, len(response_text), 2000)]
    else:
        chunks = [response_text]

    for chunk in chunks:
        message_data = {"recipient": {"id": sender_id}, "message": {"text": chunk}}

        response = requests.post(
            f"https://graph.facebook.com/v16.0/me/messages?access_token={PAGE_ACCESS_TOKEN}",
            json=message_data,
        )

        if response.status_code == 200:
            print("Message sent successfully")
        else:
            print("Failed to send message")

# Example usage:
# sender_id = "USER_ID"
# response_text = "Your long message here..."
# await send_message(sender_id, response_text)


async def handle_message(sender_id, message_text):
    response_text = await chat_with_gpt(message_text)
    await send_message(sender_id, response_text)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
