from google.genai.errors import ClientError
from google.genai import types
import logging

logger = logging.getLogger(__name__)

def create_chat(ai_client, gemini_tools, system_instruction):
    try:
        return ai_client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                tools=gemini_tools,
                system_instruction=system_instruction
            )
        )

    except Exception:
        logger.exception("Chat creation failed")
        return None


def send_to_gemini(chat, message):
    try:
        return chat.send_message(message)

    except ClientError as e:
        status_code = getattr(e, "code", None)

        logger.exception("Gemini ClientError")

        error_text = str(e)

        if "RESOURCE_EXHAUSTED" in error_text:
            return {
                "success": False,
                "message": "The AI service is currently busy. Please try again in a minute."
            }

        elif "UNAVAILABLE" in error_text:
            return {
                "success": False,
                "message": "AI service is temporarily unavailable."
            }

        elif "DEADLINE_EXCEEDED" in error_text:
            return {
                "success": False,
                "message": "The request took too long to complete."
            }

        elif "NOT_FOUND" in error_text:
            return {
                "success": False,
                "message": "AI model configuration error."
            }

        elif "UNAUTHENTICATED" in error_text:
            return {
                "success": False,
                "message": "AI service authentication failed."
            }

        elif "PERMISSION_DENIED" in error_text:
            return {
                "success": False,
                "message": "AI service access is unavailable."
            }

        return {
            "success": False,
            "message": "Unable to process your request right now."
        }

    except Exception:
        logger.exception("Unexpected Gemini error")

        return {
            "success": False,
            "message": "Something went wrong while processing your request."
        }