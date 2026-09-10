import asyncio
from typing import Callable
from urllib import parse
from xml.parsers import expat

import aiohttp
import xmltodict

from src.database import DBManager, ObjectType
from src.embed_helpers.boardgame import BoardGameObj
from src.embed_helpers.common import safeGet

BASE_URL = "https://boardgamegeek.com/xmlapi2"
USER_AGENT = "BorrowBot From Gothenburg University / Chalmers Institute of Technology (contact: heronm@chalmers.se)"
BATCH_SIZE = 20
MAX_RESULTS = 200
REQUEST_INTERVAL = 1.0
TIMEOUT = aiohttp.ClientTimeout(total=30)


class BGGUnavailable(Exception):
    pass


async def requestXML(session: aiohttp.ClientSession, url: str) -> dict:
    try:
        async with session.get(url, headers={"User-Agent": USER_AGENT}) as response:
            response.raise_for_status()
            return xmltodict.parse(await response.read())
    except (aiohttp.ClientError, asyncio.TimeoutError, expat.ExpatError) as error:
        raise BGGUnavailable(str(error)) from error


async def fetchBGGIDsFromName(name: str) -> list[int] | None:
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        data = await requestXML(session, f"{BASE_URL}/search?query={parse.quote_plus(name)}")
    items = safeGet(data, "items/item", None)
    if items is None:
        return None
    items = [items] if isinstance(items, dict) else items
    ids = [int(item["@id"]) for item in items if safeGet(item, "@type", "") == "boardgame"]
    if len(ids) == 0:
        return None
    return ids[:MAX_RESULTS]


async def fetchBGGameData(ids: list[int], extraData: dict = None, updateCallback: Callable[[int], None] = None) -> list[BoardGameObj]:
    games = []
    ids = [int(id) for id in ids]
    if len(ids) == 0:
        return games
    if extraData is None:
        extraData = {}
    for key in ids:
        if key not in extraData:
            item = DBManager.getInstance().getItemData(ObjectType.BOARDGAME, DBManager.getInstance().getIDFromBGGID(key))
            if item:
                extraData[key] = item.getDict()
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        for index in range(0, len(ids), BATCH_SIZE):
            if index > 0:
                await asyncio.sleep(REQUEST_INTERVAL)
            batch = ids[index:index + BATCH_SIZE]
            data = await requestXML(session, f"{BASE_URL}/thing?id={','.join(map(str, batch))}&stats=1")
            items = safeGet(data, "items/item", None)
            if items is None:
                continue
            items = [items] if isinstance(items, dict) else items
            for item in items:
                if safeGet(item, "@type", "") not in ("boardgame", "boardgameexpansion"):
                    continue
                games.append(BoardGameObj.createFromBGG(item, extraData.get(int(item["@id"]))))
            if updateCallback:
                updateCallback(len(games))
    return games
