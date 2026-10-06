import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, executor, types as aiogram_types
from dotenv import load_dotenv
from google import genai
from google.genai import errors
from google.genai import types as genai_types


# ============================================================
# LOAD ENV VARIABLES
# ============================================================

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing from .env")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(level=logging.INFO)


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)

MODEL_NAME = "gemini-3.8-flash"

# ============================================================
# TELEGRAM BOT
# ============================================================

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher(bot)


# ============================================================
# SIMPLE MEMORY
# ============================================================

class Reference:

    def __init__(self):
        self.response = ""


reference = Reference()


def clear_past():
    reference.response = ""


# ============================================================
# GEMINI REQUEST
# ============================================================

def generate_gemini_response(prompt: str):

    
    response = client.models.generate_content(
    model=MODEL_NAME,
    contents=prompt,
    config=genai_types.GenerateContentConfig(
        automatic_function_calling=
            genai_types.AutomaticFunctionCallingConfig(
                disable=True
            )
        )
    )

    return response.text


# ============================================================
# RETRY LOGIC
# ============================================================

async def ask_gemini(prompt: str) -> str:

    max_retries = 3

    for attempt in range(max_retries):

        try:

            # Run synchronous Gemini API call
            # in a separate thread
            answer = await asyncio.to_thread(
                generate_gemini_response,
                prompt
            )

            return answer

        except errors.ServerError as error:

            print(
                f"Gemini Server Error "
                f"(attempt {attempt + 1}/{max_retries}): "
                f"{error}"
            )

            if attempt == max_retries - 1:
                raise

            await asyncio.sleep(
                2 * (attempt + 1)
            )


# ============================================================
# /start
# ============================================================

@dispatcher.message_handler(commands=["start"])
async def welcome(
    message: aiogram_types.Message
):

    await message.reply(
        "Hi!\n"
        "I am Tele Bot 🤖\n"
        "Created by Khushi.\n\n"
        "How can I assist you?"
    )


# ============================================================
# /help
# ============================================================

@dispatcher.message_handler(commands=["help"])
async def helper(
    message: aiogram_types.Message
):

    help_command = """
Hi! I'm a Telegram bot created by Khushi.

Available commands:

/start
    Start the bot

/clear
    Clear previous conversation context

/help
    Show this help menu

You can also send me any normal message.
"""

    await message.reply(help_command)


# ============================================================
# /clear
# ============================================================

@dispatcher.message_handler(commands=["clear"])
async def clear(
    message: aiogram_types.Message
):

    clear_past()

    await message.reply(
        "Previous conversation context has been cleared."
    )


# ============================================================
# NORMAL CHAT MESSAGE
# ============================================================

@dispatcher.message_handler()
async def chat_handler(
    message: aiogram_types.Message
):

    user_message = message.text

    print(
        f"\n>>> USER:\n"
        f"{user_message}"
    )

    prompt = f"""
You are a helpful AI assistant.

Previous assistant response:
{reference.response}

Current user message:
{user_message}

Answer naturally and clearly.
"""

    try:

        answer = await ask_gemini(prompt)

        reference.response = answer

        print(
            f"\n>>> GEMINI:\n"
            f"{answer}"
        )

        await message.reply(answer)

    except errors.ServerError:

        await message.reply(
            "Gemini is currently busy. "
            "Please try again after a few seconds."
        )

    except Exception as error:

        print(
            f"\nUnexpected error:\n"
            f"{error}"
        )

        await message.reply(
            "Something went wrong. "
            "Please try again."
        )


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":

    print("Telegram bot is starting...")

    executor.start_polling(
        dispatcher,
        skip_updates=True
    )