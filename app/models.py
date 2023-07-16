from collections import OrderedDict

from thefuzz import process
from typing import Dict
from pydantic import BaseModel, RootModel

DEFAULT_SESSION_PRICE = 30
CURRENCY_SHORTHAND = {
    "p": "platinum",
    "g": "gold",
    "s": "silver",
    "c": "copper",
}
CURRENCY_CONVERSION = OrderedDict(
    platinum=1000,
    gold=100,
    silver=10,
    copper=1,
)


class Player(BaseModel):
    id: int
    first_name: str
    username: str
    num_sessions: int = 0
    account_balance: int = 0
    inventory: Dict[str, int] = {}
    # Under the hood we store the net currency value in copper pieces and
    # convert it into its largest representative metal pieces on the fly
    copper_pieces: int = 0

    def remaining_sessions(self) -> int:
        return self.account_balance // DEFAULT_SESSION_PRICE

    def get_item_qty(self, item_name: str) -> int:
        return self.inventory.get(item_name, 0)

    def get_currency_balance(self) -> OrderedDict:
        balance = OrderedDict()
        remainder = self.copper_pieces
        for denomination, value in CURRENCY_CONVERSION.items():
            num_units = remainder // value
            balance[denomination] = num_units
            remainder = remainder - (value * num_units)
            if remainder <= 0:
                break
        return balance

    def get_currency_balance_in(self, denomination: str) -> int:
        # Returns the net amount of $$ owned in the desired denomination
        if denomination not in CURRENCY_CONVERSION:
            return 0
        return self.copper_pieces // CURRENCY_CONVERSION[denomination]

    def set_currency(self, incoming_pieces: dict) -> None:
        for denomination, num_units in incoming_pieces:
            self.copper_pieces += CURRENCY_CONVERSION.get(denomination, 0) * num_units


class Players(RootModel):
    _filepath = None
    root: Dict[int, Player]

    def get_player(self, telegram_id: int, first_name: str, username: str):
        return self.root.setdefault(
            telegram_id, Player(id=telegram_id, first_name=first_name, username=username)
        )


class Item(BaseModel):
    name: str
    description: str = "No description has been added"


class Items(RootModel):
    _filepath = None
    root: Dict[str, Item]

    def contains(self, item_name: str) -> bool:
        if item_name in self.root:
            return True
        return False

    def get_item(self, item_name: str, lv_threshold: int = 65) -> Item:
        if not self.root:
            print(f"Dictionary is empty. Creating entry for {item_name}")
            item = Item(name=item_name)
            self.root[item_name] = item
            return item

        try:
            return self.root[item_name]
        except KeyError:
            result = process.extract(item_name, self.root.keys())[0]
            print(result)
            if result[1] >= lv_threshold:
                print(f"Similar item {result[0]} of Levenshtein Distance {result[1]} found")
                item_name = result[0]
            else:
                print(f"No similar item name to {item_name} found in DB. Creating entry")

        item = Item(name=item_name)
        self.root[item_name] = item
        return item
