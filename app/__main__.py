import os
from pathlib import Path

import tomllib
from telegram import Update
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from .models import Players, Items
from .serialization import persist, load

CONFIG = {}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LV_THRESHOLD = 80
DEFAULT_DATA_DIR = os.path.join(SCRIPT_DIR, os.pardir, "data")
PLAYERS, ITEMS = Players({}), Items({})


def setup():
    global CONFIG, PLAYERS, ITEMS
    config_path = os.path.join(SCRIPT_DIR, os.pardir, "config.toml")
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    print(f"Loaded config from {config_path}")

    try:
        config["general"]["lv_threshold"]
    except KeyError:
        print(
            "Levenshtein Distance threshold not specified in config file. Defaulting to {DEFAULT_LV_THRESHOLD}"
        )
        config["general"]["lv_threshold"] = DEFAULT_LV_THRESHOLD

    try:
        data_dir = config["general"]["data_dir"]
    except KeyError:
        print(
            f"Data directory not specified in config file. Defaulting to {DEFAULT_DATA_DIR}"
        )
        data_dir = DEFAULT_DATA_DIR

    players_json_filepath = os.path.join(data_dir, Players.__name__ + ".json")
    items_json_filepath = os.path.join(data_dir, Items.__name__ + ".json")
    Path(players_json_filepath).touch(exist_ok=True)
    Path(items_json_filepath).touch(exist_ok=True)

    PLAYERS._filepath = players_json_filepath
    PLAYERS = load(PLAYERS)
    ITEMS._filepath = items_json_filepath
    ITEMS = load(ITEMS)

    print(f"Data will be serialized in {data_dir}")
    return config


async def get_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PLAYERS
    player = PLAYERS.get_player(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{player.first_name}: Your Tinkertales balance is ${player.account_balance}",
        message_thread_id=update.effective_message.message_thread_id,
    )


async def set_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PLAYERS
    try:
        new_balance = int(context.args[0])
        player = PLAYERS.get_player(
            update.effective_user.id,
            update.effective_user.first_name,
            update.effective_user.username,
        )
        PLAYERS.root[update.effective_user.id].account_balance = new_balance
        response = f"{player.first_name}: Your Tinkertales balance has been set to ${player.account_balance}"
    except ValueError:
        response = "You may only set your Tinkertales balance to a numerical value"

    persist(PLAYERS)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=response,
        message_thread_id=update.effective_message.message_thread_id,
    )

async def remaining_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PLAYERS
    player = PLAYERS.get_player(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    print(player)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{player.first_name}: You have sufficient account balance for {player.remaining_sessions()} D&D sessions",
        message_thread_id=update.effective_message.message_thread_id,
    )


async def get_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PLAYERS
    player = PLAYERS.get_player(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )

    cb = player.get_currency_balance()
    cb_str = ""
    for k, v in cb:
        cb_str += f"{k}: {v},"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{player.first_name}: You own the following moni {cb_str}",
        message_thread_id=update.effective_message.message_thread_id,
    )

async def get_item_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CONFIG, PLAYERS, ITEMS
    item_name = " ".join(context.args)
    player = PLAYERS.get_player(
        update.effective_user.id,
        update.effective_user.first_name,
        update.effective_user.username,
    )
    item = ITEMS.get_item(item_name, lv_threshold=CONFIG["general"]["lv_threshold"])
    qty = player.get_item_qty(item.name)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{qty}x {item.name}",
        message_thread_id=update.effective_message.message_thread_id,
    )


async def set_item_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CONFIG, PLAYERS, ITEMS
    new_qty = int(context.args[0])
    item_name = " ".join(context.args[1:])
    try:
        player = PLAYERS.get_player(
            update.effective_user.id,
            update.effective_user.first_name,
            update.effective_user.username,
        )
        item = ITEMS.get_item(item_name, lv_threshold=CONFIG["general"]["lv_threshold"])
        item_name = item.name
        PLAYERS.root[update.effective_user.id].inventory[item_name] = new_qty
        response = (
            f"The qty of {item_name} has been set to {new_qty} for {player.username}"
        )
    except ValueError:
        response = f"The qty of {item_name} must be an integer"

    persist(PLAYERS)
    persist(ITEMS)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=response,
        message_thread_id=update.effective_message.message_thread_id,
    )


if __name__ == "__main__":
    CONFIG = setup()

    application = ApplicationBuilder().token(CONFIG["secrets"]["token"]).build()
    get_balance_handler = CommandHandler("get_balance", get_balance)
    set_balance_handler = CommandHandler("set_balance", set_balance)
    get_remaining_sessions = CommandHandler("remaining_sessions", remaining_sessions)
    get_currency_handler = CommandHandler("get_currency", get_currency)
    get_item_qty_handler = CommandHandler("get_item_qty", get_item_qty)
    set_item_qty_handler = CommandHandler("set_item_qty", set_item_qty)

    application.add_handler(get_balance_handler)
    application.add_handler(set_balance_handler)
    application.add_handler(get_remaining_sessions)
    application.add_handler(get_currency_handler)
    application.add_handler(get_item_qty_handler)
    application.add_handler(set_item_qty_handler)

    application.run_polling()
