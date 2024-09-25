from datetime import datetime, time

import pytz
from disnake import ApplicationCommandInteraction, Embed, Color, Permissions, Member
from disnake.ext.tasks import loop
from disnake.ext.commands import Cog, slash_command

from src.database import ObjectType, DBManager
from src.embed_helpers.common import Difficulty, Platform
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
            DBManager.getInstance().setReminderSent(borrow['user'])
        print("Reminders sent at " + datetime.now(tz=pytz.timezone('Europe/Stockholm')).strftime("%Y-%m-%d %H:%M:%S"))

    async def _sendQueryEmbed(self, inter: ApplicationCommandInteraction, items: list, flags: str):
        embed = items[0].getEmbed([flag.strip() for flag in flags.split(",")])
        view = ItemPaginator(items, flags, embed)
        embed.set_footer(text="Use arrows to move between pages")
        view.msg = await inter.original_response()
        await view.msg.edit(embed=embed, view=view)

    @slash_command(name="insertbg", description="Insert a new boardgame into the database", dm_permission=True)
    async def insertBoardgame(self, inter: ApplicationCommandInteraction, bgg_code: int, play_difficulty: str = "undefined", learn_difficulty: str = "undefined", copies: int = 1):
        inter.response.defer()
        if DBManager.getInstance().insertBoardgame(bgg_code, Difficulty[play_difficulty.upper()], Difficulty[learn_difficulty.upper()], copies):
            embed: Embed = Embed(title="Boardgame inserted", description=f"Boardgame inserted successfully", color=Color.green())
        else:
            embed: Embed = Embed(title="Error inserting boardgame", description=f"Error inserting boardgame, is it already present?", color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="insertvg", description="Insert a new videogame into the database", dm_permission=True)
    async def insertVideogame(self, inter: ApplicationCommandInteraction, name: str, platform: str, min_players: int, max_players: int, length: int, difficulty: str = "undefined", copies: int = 1):
        await inter.response.defer()
        if DBManager.getInstance().insertVideogame(name, Platform(platform), Difficulty(difficulty), min_players, max_players, length, copies):
            embed: Embed = Embed(title="Videogame inserted", description=f"Videogame {name} inserted successfully", color=Color.green())
        else:
            embed: Embed = Embed(title="Error inserting videogame", description=f"Error inserting videogame {name}, is it already present?", color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="insertbook", description="Insert a new book into the database", dm_permission=True)
    async def insertBook(self, inter: ApplicationCommandInteraction, name: str, author: str, pages: int, genre: str, abstract: str = "", copies: int = 1):
        await inter.response.defer()
        if DBManager.getInstance().insertBook(name, author, pages, genre, abstract, copies):
            embed: Embed = Embed(title="Book inserted", description=f"Book {name} inserted successfully", color=Color.green())
        else:
            embed: Embed = Embed(title="Error inserting book", description=f"Error inserting book {name}, is it already present?", color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="bgsearch", description="Simple command to get the list of boardgames with some filters", dm_permission=True)
    async def getBoardgames(self, inter: ApplicationCommandInteraction, name: str = "", max_difficulty: str = "", player_count: int = 0, max_length: int = 0, flags: str = "", private: bool = False):
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

    @slash_command(name="vgsearch", description="Simple command to get the list of videogames with some filters", dm_permission=True)
    async def getVideogames(self, inter: ApplicationCommandInteraction, name: str = "", max_difficulty: str = "", player_count: int = 0, platform: str = "", flags: str = "", private: bool = False):
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

    @slash_command(name="booksearch", description="Simple command to get the list of books with some filters", dm_permission=True)
    async def getBooks(self, inter: ApplicationCommandInteraction, name: str = "", author: str = "", genre: str = "", min_pages: int = 0, flags: str = "", private: bool = False):
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
        books: [dict] = DBManager.getInstance().getFilteredList(ObjectType.BOOK, "", filterStr)
        if len(books) == 0:
            embed: Embed = Embed(title="No books found", description="No books found with the specified filters", color=Color.red())
            await inter.edit_original_message(embed=embed)
            return
        await self._sendQueryEmbed(inter, books, flags)

    @slash_command(name="interest", description="Declare interest in borrowing an item from Piazza", dm_permission=True)
    async def declareInterest(self, inter: ApplicationCommandInteraction, item: str):
        await inter.response.defer()
        itemID = DBManager.getInstance().getItemIDFromName(item)
        if itemID == -1:
            embed = Embed(title="Error declaring interest", description="Item not found", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        data = DBManager.getInstance().getBorrowsList((0, 0), inter.user.id, itemID, True)
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

    @slash_command(name="uninterest", description="Cancel interest in borrowing an item from Piazza", dm_permission=True)
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

    @slash_command(name="borrow", description="Borrow something from Piazza. Dates should be written in the format YYYY-MM-DD", dm_permission=True)
    async def borrow(self, inter: ApplicationCommandInteraction, item: str, planned_return: str = None, retrieval_date: str = None):
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
            itemID = DBManager.getInstance().getItemIDFromName(item)
            if itemID == -1:
                success = False
                message = "Item not found"
            else:
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

    @slash_command(name="return", description="Return something you borrowed to Piazza", dm_permission=True)
    async def returnItem(self, inter: ApplicationCommandInteraction, item: str):
        await inter.response.defer()
        itemID = DBManager.getInstance().getItemIDFromName(item)
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

    @slash_command(name="getborrows", description="Get the list of items borrowed from Piazza", dm_permission=True)
    async def getBorrows(self, inter: ApplicationCommandInteraction, user: Member = None, private: bool = False):
        await inter.response.defer(ephemeral=private)
        amount = DBManager.getInstance().getBorrowsAmount(user.id if user is not None else None, True)
        if amount == 0:
            titleAppend = (" by " + (user.nick if user.nick is not None else user.name)) if user is not None else ""
            embed: Embed = Embed(title="Items borrowed" + titleAppend, description="No items have been borrowed from Piazza" + titleAppend, color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        embed = await DBManager.getInstance().getBorrowsListEmbed((0, 10), inter, user.id if user is not None else None, True)
        view = BorrowPaginator(amount // 10 + 1, embed, DBManager.getInstance(), user.id if user is not None else None, True)
        view.msg = await inter.original_response()
        embed.set_footer(text="Use arrows to move between pages")
        await view.msg.edit(embed=embed, view=view)

    @slash_command(name="getborrowhistory", description="Get the history of borrowed items from Piazza", dm_permission=True)
    async def getBorrowHistory(self, inter: ApplicationCommandInteraction, user: Member = None, private: bool = False):
        await inter.response.defer(ephemeral=private)
        amount = DBManager.getInstance().getBorrowsAmount(user.id if user is not None else None, False)
        if amount == 0:
            titleAppend = (" by " + (user.nick if user.nick is not None else user.name)) if user is not None else ""
            embed: Embed = Embed(title="Borrow history" + titleAppend, description="No items have been borrowed from Piazza" + titleAppend, color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        embed = await DBManager.getInstance().getBorrowsListEmbed((0, 10), inter, user.id if user is not None else None, False)
        view = BorrowPaginator(amount // 10 + 1, embed, DBManager.getInstance(), user.id if user is not None else None, False)
        view.msg = await inter.original_response()
        embed.set_footer(text="Use arrows to move between pages")
        await view.msg.edit(embed=embed, view=view)