from datetime import datetime, time
from functools import partial

import pytz
from disnake import ApplicationCommandInteraction, Embed, Color, Member
from disnake.ext.tasks import loop
from disnake.ext.commands import Cog, slash_command

from src.database import ObjectType, DBManager
from src.embed_helpers.book import BookObj
from src.embed_helpers.common import Difficulty, Platform, getBorrowsListEmbed, getBorrowsStatsEmbed
from src.utils.borrow_paginator import BorrowPaginator
from src.utils.paginator import ItemPaginator


class GamesCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @loop(time=time(hour=8, minute=0, tzinfo=pytz.timezone('Europe/Stockholm')))
    async def reminders(self):
        borrows = DBManager.getInstance().getReminders()
        for borrow in borrows:
            user = self.bot.get_user(borrow['user'])
            if user is None:
                continue
            if borrow['return_status'] == 'overdue':
                embed = Embed(title="Reminder", description=f"You are overdue to return {borrow['item_name']} ", color=Color.red())
            else:
                embed = Embed(title="Reminder", description=f"You are cheduled to return {borrow['item_name']} " + borrow['return_status'], color=Color.red())
            await user.send(embed=embed)
            DBManager.getInstance().setReminderSent(borrow['user'], borrow['item'])
        print("Reminders sent at " + datetime.now(tz=pytz.timezone('Europe/Stockholm')).strftime("%Y-%m-%d %H:%M:%S"))

    @slash_command(name="insertbg", description="Insert a new boardgame into the database")
    async def insertBoardgame(self, inter: ApplicationCommandInteraction, bgg_code: int, play_difficulty: str = "undefined", learn_difficulty: str = "undefined", copies: int = 1):
        await inter.response.defer()
        if DBManager.getInstance().insertBoardgame(bgg_code, Difficulty[play_difficulty.upper()], Difficulty[learn_difficulty.upper()], copies):
            embed: Embed = Embed(title="Boardgame inserted", description=f"Boardgame inserted successfully", color=Color.green())
        else:
            embed: Embed = Embed(title="Error inserting boardgame", description=f"Error inserting boardgame, is it already present?", color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="insertvg", description="Insert a new videogame into the database")
    async def insertVideogame(self, inter: ApplicationCommandInteraction, name: str, platform: str, min_players: int, max_players: int, length: int, difficulty: str = "undefined", copies: int = 1):
        await inter.response.defer()
        if DBManager.getInstance().insertVideogame(name, Platform[platform.upper()], Difficulty[difficulty.upper()], min_players, max_players, length, copies):
            embed: Embed = Embed(title="Videogame inserted", description=f"Videogame {name} inserted successfully", color=Color.green())
        else:
            embed: Embed = Embed(title="Error inserting videogame", description=f"Error inserting videogame {name}, is it already present?", color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="insertbook", description="Insert a new book into the database")
    async def insertBook(self, inter: ApplicationCommandInteraction, name: str, author: str, pages: int, genre: str, abstract: str = "", copies: int = 1):
        await inter.response.defer()
        if DBManager.getInstance().insertBook(name, author, pages, genre, abstract, copies):
            embed: Embed = Embed(title="Book inserted", description=f"Book {name} inserted successfully", color=Color.green())
        else:
            embed: Embed = Embed(title="Error inserting book", description=f"Error inserting book {name}, is it already present?", color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="bgsearch", description="Simple command to get the list of boardgames with some filters")
    async def getBoardgames(self, inter: ApplicationCommandInteraction, name: str = "", max_difficulty: str = "", player_count: int = 0, max_length: int = 0, flags: str = "", private: bool = True):
        await inter.response.defer(ephemeral=private)
        filters: [str] = []
        if name:
            filters.append(f"name=={name}")
        if max_difficulty:
            filters.append(f"play<={max_difficulty}")
        if player_count > 0:
            filters.append(f"max_players>={player_count}")
            filters.append(f"min_players<={player_count}")
        if max_length > 0:
            filters.append(f"length<={max_length}")
        filterStr: str = ", ".join(filters)
        games: [dict] = DBManager.getInstance().getFilteredList(ObjectType.BOARDGAME, "", filterStr)
        if len(games) == 0:
            embed: Embed = Embed(title="No boardgames found", description="No boardgames found with the specified filters", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        await self._sendQueryEmbed(inter, games, flags)

    @slash_command(name="vgsearch", description="Simple command to get the list of videogames with some filters")
    async def getVideogames(self, inter: ApplicationCommandInteraction, name: str = "", max_difficulty: str = "", player_count: int = 0, platform: str = "", flags: str = "", private: bool = True):
        await inter.response.defer(ephemeral=private)
        filters: [str] = []
        if name:
            filters.append(f"name=={name}")
        if max_difficulty:
            filters.append(f"play<={max_difficulty}")
        if player_count > 0:
            filters.append(f"max_players>={player_count}")
            filters.append(f"min_players<={player_count}")
        if platform:
            filters.append(f"platform=={platform}")
        filterStr: str = ", ".join(filters)
        games: [dict] = DBManager.getInstance().getFilteredList(ObjectType.VIDEOGAME, "", filterStr)
        if len(games) == 0:
            embed: Embed = Embed(title="No videogames found", description="No videogames found with the specified filters", color=Color.red())
            await inter.edit_original_message(embed=embed)
            return
        await self._sendQueryEmbed(inter, games, flags)

    @slash_command(name="booksearch", description="Simple command to get the list of books with some filters")
    async def getBooks(self, inter: ApplicationCommandInteraction, name: str = "", author: str = "", genre: str = "", min_pages: int = 0, flags: str = "", private: bool = True):
        await inter.response.defer(ephemeral=private)
        filters: [str] = []
        if name:
            filters.append(f"name=={name}")
        if author:
            filters.append(f"author=={author}")
        if genre:
            filters.append(f"genre=={genre}")
        if min_pages > 0:
            filters.append(f"pages>={min_pages}")
        filterStr: str = ", ".join(filters)
        books: [BookObj] = DBManager.getInstance().getFilteredList(ObjectType.BOOK, "", filterStr)
        if len(books) == 0:
            embed: Embed = Embed(title="No books found", description="No books found with the specified filters", color=Color.red())
            await inter.edit_original_message(embed=embed)
            return
        await self._sendQueryEmbed(inter, books, flags)

    @slash_command(name="interest", description="Declare interest in borrowing an item from Piazza")
    async def declareInterest(self, inter: ApplicationCommandInteraction, item: str):
        await inter.response.defer()
        itemID = DBManager.getInstance().getItemIDFromName(item)
        if itemID == -1:
            embed = Embed(title="Error declaring interest", description="Item not found", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        data = DBManager.getInstance().getBorrowsList(inter.user.id, itemID, True)
        success = DBManager.getInstance().declareInterest(inter.user.id, itemID)
        if not success:
            embed = Embed(title="Error declaring interest", description="You have already declared interest for this item", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        embed = Embed(
            title=f"Someone declared interest for the game {DBManager.getInstance().getItemNameFromID(itemID)}",
            description="Don't worry! This does not mean you have to return it right away. It just means someone wants to borrow it too. Just make sure to return it as soon as you are done with it!",
            color=Color.orange())
        for entry in data:
            userObj = await inter.guild.fetch_member(entry['user'])
            if userObj.id == inter.user.id:
                continue
            await userObj.send(embed=embed)
        embed = Embed(title="Interest declared successfully", description="You will be notified when someone returns or borrows the game", color=Color.green())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="uninterest", description="Cancel interest in borrowing an item from Piazza")
    async def cancelInterest(self, inter: ApplicationCommandInteraction, item: str):
        await inter.response.defer()
        itemID = DBManager.getInstance().getItemIDFromName(item)
        if itemID == -1:
            embed = Embed(title="Error cancelling interest", description="Item not found", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        success = DBManager.getInstance().cancelInterest(inter.user.id, itemID)
        if not success:
            embed = Embed(title="Error cancelling interest", description="You have not declared interest for this item", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        embed = Embed(
            title=f"Cancelled interest successfully",
            description=f"You will no longer be notified when someone returns or borows the game {DBManager.getInstance().getItemNameFromID(itemID)}",
            color=Color.orange())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="borrow", description="Borrow something from Piazza. Dates should be written in the format YYYY-MM-DD")
    async def borrowItem(self, inter: ApplicationCommandInteraction, item: str, planned_return: str = None, retrieval_date: str = None):
        await inter.response.defer()
        itemID = None
        try:
            if retrieval_date:
                retrieval_date = datetime.strptime(retrieval_date, "%Y-%m-%d")
            if planned_return:
                planned_return = datetime.strptime(planned_return, "%Y-%m-%d").replace(hour=12)
        except ValueError:
            success = False
            message = "Error parsing dates, please use the format YYYY-MM-DD"
        else:
            itemIDs = DBManager.getInstance().getItemsToBorrowFromName(inter.user.id, item)
            if len(itemIDs) == 0:
                success = False
                message = "Item not found"
            elif len(itemIDs) > 1:
                success = False
                gameNames = ["- " + DBManager.getInstance().getItemNameFromID(entry) for entry in itemIDs]
                if len(gameNames) > 15:
                    gameList = "\n".join(gameNames[:15]) + f"\n(+{len(gameNames) - 15})"
                else:
                    gameList = "\n".join(gameNames)
                message = "**Multiple items found:**\n" + gameList + "\n\n**Please be more specific.**"
            else:
                itemID = itemIDs[0]
                success, message = DBManager.getInstance().borrowItem(inter.user.id, itemID, planned_return, retrieval_date)
        if success:
            data = DBManager.getInstance().getInterested(itemID)
            availableCopies = DBManager.getInstance().getItemAvailableCopies(itemID)
            if availableCopies == 0:
                description = "There are no available copies of this game at the moment. You will be notified when someone returns it."
            else:
                description = f"There are still {availableCopies} available copies of this game."
            dmEmbed = Embed(title=f"Someone borrowed the game {DBManager.getInstance().getItemNameFromID(itemID)}", description=description, color=Color.orange() if availableCopies == 0 else Color.yellow())
            removedInterest = False
            for entry in data:
                if entry['user'] == inter.user.id:
                    DBManager.getInstance().cancelInterest(entry['user'], itemID)
                    removedInterest = True
                    continue
                userObj = await inter.guild.fetch_member(entry['user'])
                await userObj.send(embed=dmEmbed)
            if removedInterest:
                message += "\nYou have been removed from the interest list for this game."
            embed: Embed = Embed(title="Item borrowed", description=message, color=Color.green())
        else:
            embed: Embed = Embed(title="Error borrowing item", description=message, color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="return", description="Return something you borrowed to Piazza")
    async def returnItem(self, inter: ApplicationCommandInteraction, item: str):
        await inter.response.defer()
        itemIDs = DBManager.getInstance().getItemsToReturnFromName(inter.user.id, item)
        if len(itemIDs) == 0:
            embed = Embed(title="Error returning item", description="Item not found", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        elif len(itemIDs) > 1:
            gameNames = ["- " + DBManager.getInstance().getItemNameFromID(entry) for entry in itemIDs]
            if len(gameNames) > 15:
                gameList = "\n".join(gameNames[:15]) + f"\n(+{len(gameNames) - 15})"
            else:
                gameList = "\n".join(gameNames)
            embed = Embed(title="Error returning item", description="**Multiple items found:**\n" + gameList + "\n\n**Please be more specific.**", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        else:
            itemID = itemIDs[0]
            success, message = DBManager.getInstance().returnItem(inter.user.id, itemID)
        if not success:
            embed = Embed(title="Error returning item", description=message, color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        embed = Embed(title="Item returned", description=message, color=Color.green())
        await inter.edit_original_response(embed=embed)
        data = DBManager.getInstance().getInterested(itemID)
        availableCopies = DBManager.getInstance().getItemAvailableCopies(itemID)
        description = f"There are {availableCopies} available copies of this game."
        dmEmbed = Embed(title=f"Someone returned the game {DBManager.getInstance().getItemNameFromID(itemID)}", description=description, color=Color.green())
        for entry in data:
            userObj = await inter.guild.fetch_member(entry['user'])
            await userObj.send(embed=dmEmbed)

    @staticmethod
    async def execGetBorrowsCommand(inter: ApplicationCommandInteraction, current: bool, user: Member = None, private: bool = True):
        await inter.response.defer(ephemeral=private)
        amount = DBManager.getInstance().getBorrowsAmount(user.id if user is not None else None, current)
        if amount == 0:
            titleAppend = (" by " + (user.nick if user.nick is not None else user.name)) if user is not None else ""
            embed: Embed = Embed(title="Items borrowed" + titleAppend, description="No items have been borrowed from Piazza" + titleAppend, color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        items = DBManager.getInstance().getBorrowsList(user.id if user is not None else None, None, current)
        for item in items:
            item['user'] = (await inter.guild.fetch_member(item['user'])).mention
        embed = getBorrowsListEmbed(items[:9], user, current)
        view = BorrowPaginator(items, embed, partial(getBorrowsListEmbed, user=user, current=current))
        view.msg = await inter.original_response()
        embed.set_footer(text="Use arrows to move between pages")
        await view.msg.edit(embed=embed, view=view)

    @slash_command(name="getborrows", description="Get the list of items borrowed from Piazza")
    async def getBorrows(self, inter: ApplicationCommandInteraction, user: Member = None, private: bool = True):
        await GamesCog.execGetBorrowsCommand(inter, True, user, private)

    @slash_command(name="getborrowhistory", description="Get the history of borrowed items from Piazza")
    async def getBorrowHistory(self, inter: ApplicationCommandInteraction, user: Member = None, private: bool = True):
        await GamesCog.execGetBorrowsCommand(inter, False, user, private)

    @slash_command(name="getborrowstats", description="Get the borrow highscores!")
    async def getBorrowStats(self, inter: ApplicationCommandInteraction, order: str = "amount", private: bool = True):
        await inter.response.defer(ephemeral=private)
        if order not in ["time", "amount", "count", "current"]:
            order = "total"
        elif order == "amount" or order == "count":
            order = "total"
        data = DBManager.getInstance().getBorrowStats(order)
        if len(data) == 0:
            embed = Embed(title="No borrow stats retrieved", description="Either this is a very weird error or no one has borrowed anything yet", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        for entry in data:
            entry['user'] = await inter.guild.fetch_member(entry['user'])
        embed = getBorrowsStatsEmbed(data, order)
        view = BorrowPaginator(data, embed, partial(getBorrowsStatsEmbed, order=order))
        view.msg = await inter.original_response()
        embed.set_footer(text="Use arrows to move between pages")
        await view.msg.edit(embed=embed, view=view)

    @staticmethod
    async def _sendQueryEmbed(inter: ApplicationCommandInteraction, items: list, flags: str):
        embed = items[0].getEmbed([flag.strip() for flag in flags.split(",")])
        view = ItemPaginator(items, flags, embed)
        embed.set_footer(text="Use arrows to move between pages")
        view.msg = await inter.original_response()
        await view.msg.edit(embed=embed, view=view)
