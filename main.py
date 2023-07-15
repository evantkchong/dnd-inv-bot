import os
import json
import tomllib
from dataclasses import dataclass, asdict

from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

@dataclass
class Player:
    first_name: str
    username: str
    num_sessions: int = 0
    account_balance: float = 0.0

class Players(dict):
    def query(self, telegram_id, first_name, username):
        return self.setdefault(
        telegram_id,
        Player(first_name=first_name, username=username)
    )

    def as_dict(self):
        return {k:asdict(v) for k, v in self.items()}

    def serialize(self):
        return json.dumps(self.as_dict())

    def save(self, filepath):
        with open(filepath) as f:
            json.dump(self.as_dict, f)

    @classmethod
    def deserialize(cls, json_str):
        json_dict = json.loads(json_str)
        output = cls()
        for k, v in json_dict.items():
            output[k] = Player(**v)
        return output

    @classmethod
    def load(cls, filepath):
        with open(filepath) as f:
            data = json.load(f)
        return cls.deserialize(data)

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

# async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

async def get_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # adds = {}
    global PLAYERS
    player = PLAYERS.query(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hello {player.first_name}, your Tinkertales balance is ${player.account_balance}",
        message_thread_id=update.message.message_thread_id
    )

async def set_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_balance = float(context.args[0])
        global PLAYERS
        player = PLAYERS.query(
            update.effective_user.id,
            update.effective_user.first_name,
            update.effective_user.username
        )
        PLAYERS[update.effective_user.id].account_balance = new_balance
        response = f"Your Tinkertales balance has been set to ${player.account_balance}"
    except ValueError:
        response = "You may only set your Tinkertales balance to a numerical value"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response, message_thread_id=update.message.message_thread_id)


# async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     # text_caps = ' '.join(context.args).upper()
#     print(update.message.text)
#     text_caps = ''.join(update.message.text).upper()
#     print(update)
#     await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)

if __name__ == "__main__":
    with open(os.path.join(SCRIPT_DIR, "config.toml"), "rb") as f:
        config = tomllib.load(f)

    PLAYERS = Players()
    filepath = config["general"]["filepath"]
    if os.path.exists(filepath):
        PLAYERS = Players.load(filepath)

    application = ApplicationBuilder().token(config["secrets"]["token"]).build()
    get_balance_handler = CommandHandler('get_balance', get_balance)
    set_balance_handler = CommandHandler('set_balance', set_balance)

    application.add_handler(get_balance_handler)
    application.add_handler(set_balance_handler)

    # start_handler = CommandHandler('start', start)
    # Any text that is not a command
    # echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    # caps_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), caps)

    # application.add_handler(start_handler)
    # application.add_handler(echo_handler)
    # application.add_handler(caps_handler)

    application.run_polling()