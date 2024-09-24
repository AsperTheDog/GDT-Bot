from typing import Callable

import requests
import xmltodict
from urllib import parse

from src.database import DBManager, ObjectType
from src.embed_helpers.boardgame import BoardGameObj


def fetchBGGIDsFromName(name: str):
    ids = []
    url = f"https://boardgamegeek.com/xmlapi2/search?query={parse.quote_plus(name)}"
    response = requests.get(url)
    response.raise_for_status()
    items = xmltodict.parse(response.content)
    if "items" not in items or "item" not in items["items"]:
        return None
    items = items["items"]["item"]
    items = [items] if isinstance(items, dict) else items
    for item in items:
        if item["@type"] != "boardgame":
            continue
        ids.append(int(item["@id"]))
    if len(ids) == 0:
        return None
    if len(ids) > 200:
        return ids[:200]
    return ids


def fetchBGGameData(ids: [int], extraData: dict = None, updateCallback: Callable[[int], None] = None) -> [BoardGameObj]:
    games = []
    # fetch in batches of 20 games
    for i in range(0, len(ids), 20):
        nextAmount = min(20, len(ids) - i)
        url = f'https://boardgamegeek.com/xmlapi2/thing?id={",".join(map(str, ids[i:i + nextAmount]))}&stats=1'
        response = requests.get(url)
        response.raise_for_status()

        if extraData is None:
            extraData = {}

        for key in ids:
            if key not in extraData:
                res = DBManager.getInstance().getItemData(ObjectType.BOARDGAME, DBManager.getInstance().getIDFromBGGID(key))
                if res:
                    extraData[key] = res.getDict()

        items = xmltodict.parse(response.content)
        if "items" not in items or "item" not in items["items"]:
            return None
        items = items["items"]["item"]
        items = [items] if isinstance(items, dict) else items
        for item in items:
            if item["@type"] != "boardgame":
                continue
            game = BoardGameObj.createFromBGG(item, extraData[item["@id"]] if item["@id"] in extraData else None)
            games.append(game)
        if updateCallback:
            updateCallback(len(games))
    return games
