import asyncio
from collections.abc import Collection

import discord

MAX_CONCURRENT_FETCHES = 10


async def fetchUser(bot: discord.Client, userID: int) -> discord.User | None:
    user = bot.get_user(userID)
    if user is not None:
        return user
    try:
        return await bot.fetch_user(userID)
    except discord.HTTPException:
        return None


async def fetchUsers(bot: discord.Client, userIDs: Collection[int]) -> dict[int, discord.User]:
    unique = list(dict.fromkeys(userIDs))
    if len(unique) == 0:
        return {}
    limit = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)

    async def fetch(userID: int) -> discord.User | None:
        async with limit:
            return await fetchUser(bot, userID)

    resolved = await asyncio.gather(*(fetch(userID) for userID in unique))
    return {userID: user for userID, user in zip(unique, resolved) if user is not None}


async def sendDirectMessage(user: discord.User, embed: discord.Embed) -> bool:
    try:
        await user.send(embed=embed)
    except discord.HTTPException:
        return False
    return True
