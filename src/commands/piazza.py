from datetime import datetime, time

import pytz
from disnake import ApplicationCommandInteraction, Embed, Color, Permissions, Member
from disnake.ext.tasks import loop
from disnake.ext.commands import Cog, slash_command

from src.database import ObjectType
from src.utils.borrow_paginator import BorrowPaginator
from src.utils.paginator import GamePaginator


class GamesCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @loop(time=time(hour=8, minute=0, tzinfo=pytz.timezone('Europe/Stockholm')))
    async def reminders(self):
        borrows = self.bot.db.getReminders()
        for borrow in borrows:
            user = self.bot.get_user(borrow['user'])
            if user is None:
                continue
            if borrow['return_status'] == 'overdue':
                embed = Embed(title="Reminder", description=f"You are overdue to return {borrow['item_name']} ", color=Color.red())
            else:
                embed = Embed(title="Reminder", description=f"You are cheduled to return {borrow['item_name']} " + borrow['return_status'], color=Color.red())
            await user.send(embed=embed)
            self.bot.db.setReminderSent(borrow['user'])
        print("Reminders sent at " + datetime.now(tz=pytz.timezone('Europe/Stockholm')).strftime("%Y-%m-%d %H:%M:%S"))

    async def _sendQueryEmbed(self, inter: ApplicationCommandInteraction, itemType: ObjectType, items: [dict], flags: str):
        embed: Embed = self.bot.db.getItemEmbed(itemType, items[0]['id'], "e" in flags)
        view = GamePaginator(itemType, items, "e" in flags, embed, self.bot.db)
        embed.set_footer(text="Use arrows to move between pages")
        view.msg = await inter.original_response()
        await view.msg.edit(embed=embed, view=view)

    @slash_command(name="insertbg", description="Insert a new boardgame into the database", permissions=Permissions(administrator=True))
    async def insertBoardgame(self, inter: ApplicationCommandInteraction, bgg_code: int, name: str, min_players: int, max_players: int, length: int, play_difficulty: str = "undefined", learn_difficulty: str = "undefined", copies: int = 1):
        if self.bot.db.insertBoardgame(bgg_code, name, play_difficulty, learn_difficulty, min_players, max_players, length, copies):
            embed: Embed = Embed(title="Boardgame inserted", description=f"Boardgame {name} inserted successfully", color=Color.green())
        else:
            embed: Embed = Embed(title="Error inserting boardgame", description=f"Error inserting boardgame {name}, is it already present?", color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="insertvg", description="Insert a new videogame into the database", permissions=Permissions(administrator=True))
    async def insertVideogame(self, inter: ApplicationCommandInteraction, name: str, platform: str, min_players: int, max_players: int, length: int, difficulty: str = "undefined", copies: int = 1):
        await inter.response.defer()
        if self.bot.db.insertVideogame(name, platform, difficulty, min_players, max_players, length, copies):
            embed: Embed = Embed(title="Videogame inserted", description=f"Videogame {name} inserted successfully", color=Color.green())
        else:
            embed: Embed = Embed(title="Error inserting videogame", description=f"Error inserting videogame {name}, is it already present?", color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="insertbook", description="Insert a new book into the database", permissions=Permissions(administrator=True))
    async def insertBook(self, inter: ApplicationCommandInteraction, name: str, author: str, pages: int, genre: str, abstract: str = "", copies: int = 1):
        await inter.response.defer()
        if self.bot.db.insertBook(name, author, pages, genre, abstract, copies):
            embed: Embed = Embed(title="Book inserted", description=f"Book {name} inserted successfully", color=Color.green())
        else:
            embed: Embed = Embed(title="Error inserting book", description=f"Error inserting book {name}, is it already present?", color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="bgsearch", description="Simple command to get the list of boardgames with some filters")
    async def getBoardgames(self, inter: ApplicationCommandInteraction, name: str = "", max_difficulty: str = "", player_count: int = 0, max_length: int = 0, flags: str = ""):
        await inter.response.defer()
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
        print("Performing boardgame simple query...")
        games: [dict] = self.bot.db.getFilteredList(ObjectType.BOARDGAME, "", filterStr)
        if len(games) == 0:
            embed: Embed = Embed(title="No boardgames found", description="No boardgames found with the specified filters", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        await self._sendQueryEmbed(inter, ObjectType.BOARDGAME, games, flags)

    @slash_command(name="vgsearch", description="Simple command to get the list of videogames with some filters")
    async def getVideogames(self, inter: ApplicationCommandInteraction, name: str = "", max_difficulty: str = "", player_count: int = 0, platform: str = "", flags: str = ""):
        await inter.response.defer()
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
        print("Performing videogame simple query...")
        games: [dict] = self.bot.db.getFilteredList(ObjectType.VIDEOGAME, "", filterStr)
        if len(games) == 0:
            embed: Embed = Embed(title="No videogames found", description="No videogames found with the specified filters", color=Color.red())
            await inter.edit_original_message(embed=embed)
            return
        await self._sendQueryEmbed(inter, ObjectType.VIDEOGAME, games, flags)

    @slash_command(name="booksearch", description="Simple command to get the list of books with some filters")
    async def getBooks(self, inter: ApplicationCommandInteraction, name: str = "", author: str = "", genre: str = "", min_pages: int = 0, flags: str = ""):
        await inter.response.defer()
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
        print("Performing book simple query...")
        books: [dict] = self.bot.db.getFilteredList(ObjectType.BOOK, "", filterStr)
        if len(books) == 0:
            embed: Embed = Embed(title="No books found", description="No books found with the specified filters", color=Color.red())
            await inter.edit_original_message(embed=embed)
            return
        await self._sendQueryEmbed(inter, ObjectType.BOOK, books, flags)

    @slash_command(name="borrow", description="Borrow something from Piazza. Dates should be written in the format YYYY-MM-DD")
    async def borrow(self, inter: ApplicationCommandInteraction, item: str, planned_return: str = None, retrieval_date: str = None):
        await inter.response.defer()
        try:
            if retrieval_date:
                retrieval_date = datetime.strptime(retrieval_date, "%Y-%m-%d")
            if planned_return:
                planned_return = datetime.strptime(planned_return, "%Y-%m-%d").replace(hour=12)
        except ValueError:
            success = False
            message = "Error parsing dates, please use the format YYYY-MM-DD"
        except KeyError:
            success = False
            message = "Invalid item type, options are: book, boardgame, videogame"
        else:
            try:
                itemID = int(item)
                success, message = self.bot.db.borrowItem(inter.user.id, itemID, planned_return, retrieval_date)
                if not success and message == "This item does not exist":
                    raise ValueError
            except ValueError:
                itemID = self.bot.db.getItemIDFromName(item)
                if itemID == -1:
                    success = False
                    message = "Item not found"
                else:
                    success, message = self.bot.db.borrowItem(inter.user.id, itemID, planned_return, retrieval_date)
        if success:
            embed: Embed = Embed(title="Item borrowed", description=message, color=Color.green())
        else:
            embed: Embed = Embed(title="Error borrowing item", description=message, color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="return", description="Return something you borrowed to Piazza")
    async def returnItem(self, inter: ApplicationCommandInteraction, item: str):
        await inter.response.defer()
        success, message = self.bot.db.returnItem(inter.user.id, item)
        if not success:
            embed = Embed(title="Error returning item", description=message, color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        embed = Embed(title="Item returned", description=message, color=Color.green())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="getborrows", description="Get the list of items borrowed from Piazza")
    async def getBorrows(self, inter: ApplicationCommandInteraction, user: Member = None):
        await inter.response.defer()
        amount = self.bot.db.getBorrowsAmount(user.id if user is not None else None, True)
        if amount == 0:
            titleAppend = (" by " + (user.nick if user.nick is not None else user.name)) if user is not None else ""
            embed: Embed = Embed(title="Items borrowed" + titleAppend, description="No items have been borrowed from Piazza" + titleAppend, color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        embed = await self.bot.db.getBorrowsListEmbed((0, 10), inter, user.id if user is not None else None, True)
        view = BorrowPaginator(amount // 10 + 1, embed, self.bot.db, user.id if user is not None else None)
        view.msg = await inter.original_response()
        embed.set_footer(text="Use arrows to move between pages")
        await view.msg.edit(embed=embed, view=view)

    @slash_command(name="getborrowhistory", description="Get the history of borrowed items from Piazza")
    async def getBorrowHistory(self, inter: ApplicationCommandInteraction, user: Member = None):
        await inter.response.defer()
        amount = self.bot.db.getBorrowsAmount(user.id if user is not None else None, False)
        if amount == 0:
            titleAppend = (" by " + (user.nick if user.nick is not None else user.name)) if user is not None else ""
            embed: Embed = Embed(title="Borrow history" + titleAppend, description="No items have been borrowed from Piazza" + titleAppend, color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        embed = await self.bot.db.getBorrowsListEmbed((0, 10), inter, user.id if user is not None else None, False)
        view = BorrowPaginator(amount // 10 + 1, embed, self.bot.db, user.id if user is not None else None)
        view.msg = await inter.original_response()
        embed.set_footer(text="Use arrows to move between pages")
        await view.msg.edit(embed=embed, view=view)