from functools import wraps
import json
import logging

logger = logging.getLogger(__name__)


class ToolValidationError(Exception):
    pass

def success_response(data=None, message=None):
    return json.dumps({"success": True, "message": message, "data": data}, default=str)


def error_response(message):
    return json.dumps({"success": False, "message": message, "data": None})


def tool_error_handler(func):

    @wraps(func)
    async def wrapper(*args, **kwargs):

        try:
            return await func(*args, **kwargs)

        except ToolValidationError as e:

            return error_response(str(e))

        except Exception:

            logger.exception(f"MCP Tool Failed: {func.__name__}")

            return error_response("Internal server error.")

    return wrapper
