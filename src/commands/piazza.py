from datetime import datetime, time
from functools import partial
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

from src.bgg import BGGUnavailable
from src.database import DEFAULT_DESCRIPTION, DEFAULT_THUMBNAIL, DBManager, ObjectType, Operation
from src.embed_helpers.common import Difficulty, Platform, getBorrowsItemStatsEmbed, getBorrowsListEmbed, getBorrowsStatsEmbed, mention
from src.utils.autocomplete import (bookAuthorAutocomplete, bookAutocomplete, bookNameAutocomplete, boardgameAutocomplete, boardgameNameAutocomplete,
                                    borrowableAutocomplete, interestAutocomplete, itemAutocomplete, returnableAutocomplete, videogameAutocomplete,
                                    videogameNameAutocomplete)
from src.utils.confirm import ConfirmView
from src.utils.modals import DETAIL_ENUMS, DetailsModal, DetailsView, InsertBookModal, InsertGameModal
from src.utils.paginator import PAGE_SIZE, ItemPaginator, LazyPaginator, countPages
from src.utils.users import fetchUser, fetchUsers, sendDirectMessage

TIMEZONE = ZoneInfo("Europe/Stockholm")
DIFFICULTY_CHOICES = [app_commands.Choice(name=difficulty.name.lower(), value=difficulty.name) for difficulty in Difficulty]
PLATFORM_CHOICES = [app_commands.Choice(name=platform.name.lower(), value=platform.name) for platform in Platform]
BORROW_ORDER_CHOICES = [app_commands.Choice(name=order, value=order) for order in ["amount", "time", "current", "usertime"]]
ITEM_LABELS = {ObjectType.BOARDGAME: "Boardgame", ObjectType.VIDEOGAME: "Videogame", ObjectType.BOOK: "Book"}
BORROW_TARGET_CHOICES = [app_commands.Choice(name=target, value=target) for target in ["user", "item"]]


class GamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    async def cog_load(self):
        self.reminders.start()

    async def cog_unload(self):
        self.reminders.cancel()

    @tasks.loop(time=time(hour=8, minute=0, tzinfo=TIMEZONE))
    async def reminders(self):
        borrows = DBManager.getInstance().getReminders()
        for borrow in borrows:
            user = await fetchUser(self.bot, borrow['user'])
            if user is None:
                continue
            if borrow['return_status'] == 'overdue':
                embed = discord.Embed(title="Reminder", description=f"You are overdue to return {borrow['item_name']} ", color=discord.Color.red())
            else:
                embed = discord.Embed(title="Reminder", description=f"You are cheduled to return {borrow['item_name']} " + borrow['return_status'], color=discord.Color.red())
            if await sendDirectMessage(user, embed):
                DBManager.getInstance().setReminderSent(borrow['user'], borrow['item'])
        print("Reminders sent at " + datetime.now(tz=TIMEZONE).strftime("%Y-%m-%d %H:%M:%S"))

    @app_commands.command(name="insertbg", description="Insert a new boardgame into the database")
    async def insertBoardgame(self, interaction: discord.Interaction):
        await interaction.response.send_modal(InsertGameModal("Insert a boardgame", self.insertBoardgameForm))

    async def insertBoardgameForm(self, interaction: discord.Interaction, modal: InsertGameModal):
        values = GamesCog.parseFormNumbers(modal)
        if values is None:
            embed = discord.Embed(title="Error inserting boardgame", description="Min players, max players, length and copies must be numbers and cannot be negative", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
            return
        min_players, max_players, length, copies = values
        name = modal.game_name.component.value
        existing = DBManager.getInstance().getItemIDByExactName(name)
        itemID = DBManager.getInstance().insertBoardgameManual(name, min_players, max_players, length, "", "", [], copies, -1, Difficulty.UNDEFINED, Difficulty.UNDEFINED)
        if itemID is None:
            embed = discord.Embed(title="Error inserting boardgame", description=f"Error inserting boardgame {name}, is it already present?", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
            return
        if existing != -1:
            embed = discord.Embed(title="Boardgame updated", description=f"Boardgame {name} was already in the database, {copies} copies were added to it", color=discord.Color.green())
        else:
            embed = discord.Embed(title="Boardgame inserted", description=f"Boardgame inserted successfully", color=discord.Color.green())
        view = DetailsView(interaction.user.id, ObjectType.BOARDGAME, itemID, self.applyDetails)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="insertbgg", description="Insert a new boardgame into the database by fetching it from BoardGameGeek")
    @app_commands.describe(bgg_code="BGG id of the boardgame", copies="Number of copies to add",
                           play_difficulty="How hard the game is to play", learn_difficulty="How hard the game is to learn")
    @app_commands.choices(play_difficulty=DIFFICULTY_CHOICES, learn_difficulty=DIFFICULTY_CHOICES)
    async def insertBoardgameBGG(self, interaction: discord.Interaction, bgg_code: int, copies: app_commands.Range[int, 0] = 1,
                                 play_difficulty: str = "undefined", learn_difficulty: str = "undefined"):
        await interaction.response.defer()
        if not self.bot.config.bggEnabled:
            embed = discord.Embed(title="Error inserting boardgame", description=f"BoardGameGeek is disabled, insert the boardgame with /insertbg instead", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        try:
            success = await DBManager.getInstance().insertBoardgameFromBGG(bgg_code, Difficulty[play_difficulty.upper()], Difficulty[learn_difficulty.upper()], copies)
        except BGGUnavailable:
            embed = discord.Embed(title="Error inserting boardgame", description=f"BoardGameGeek is unavailable, insert the boardgame with /insertbg instead", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        if not success:
            embed = discord.Embed(title="Error inserting boardgame", description=f"Error inserting boardgame, is the BGG ID correct?", color=discord.Color.red())
        else:
            embed = discord.Embed(title="Boardgame inserted", description=f"Boardgame inserted successfully", color=discord.Color.green())
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="insertvg", description="Insert a new videogame into the database")
    async def insertVideogame(self, interaction: discord.Interaction):
        await interaction.response.send_modal(InsertGameModal("Insert a videogame", self.insertVideogameForm))

    async def insertVideogameForm(self, interaction: discord.Interaction, modal: InsertGameModal):
        values = GamesCog.parseFormNumbers(modal)
        if values is None:
            embed = discord.Embed(title="Error inserting videogame", description="Min players, max players, length and copies must be numbers and cannot be negative", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
            return
        min_players, max_players, length, copies = values
        name = modal.game_name.component.value
        existing = DBManager.getInstance().getItemIDByExactName(name)
        itemID = DBManager.getInstance().insertVideogame(name, Platform.UNDEFINED, Difficulty.UNDEFINED, min_players, max_players, length, copies)
        if itemID is None:
            embed = discord.Embed(title="Error inserting videogame", description=f"Error inserting videogame {name}, is it already present?", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
            return
        if existing != -1:
            embed = discord.Embed(title="Videogame updated", description=f"Videogame {name} was already in the database, {copies} copies were added to it", color=discord.Color.green())
        else:
            embed = discord.Embed(title="Videogame inserted", description=f"Videogame {name} inserted successfully", color=discord.Color.green())
        view = DetailsView(interaction.user.id, ObjectType.VIDEOGAME, itemID, self.applyDetails)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @staticmethod
    def parseFormNumbers(modal: InsertGameModal) -> tuple[int, int, int, int] | None:
        try:
            values = (int(modal.min_players.component.value), int(modal.max_players.component.value),
                      int(modal.length.component.value), int(modal.copies.component.value))
        except ValueError:
            return None
        if any(value < 0 for value in values):
            return None
        return values

    @app_commands.command(name="insertbook", description="Insert a new book into the database")
    async def insertBook(self, interaction: discord.Interaction):
        await interaction.response.send_modal(InsertBookModal(self.insertBookForm))

    async def insertBookForm(self, interaction: discord.Interaction, modal: InsertBookModal):
        try:
            pages = int(modal.pages.component.value)
            copies = int(modal.copies.component.value)
        except ValueError:
            embed = discord.Embed(title="Error inserting book", description="The pages and copies must be numbers", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
            return
        name = modal.book_title.component.value
        existing = DBManager.getInstance().getItemIDByExactName(name)
        itemID = DBManager.getInstance().insertBook(name, modal.author.component.value, pages, modal.abstract.component.value, copies)
        if itemID is None:
            embed = discord.Embed(title="Error inserting book", description=f"Error inserting book {name}, is it already present?", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
            return
        if existing != -1:
            embed = discord.Embed(title="Book updated", description=f"Book {name} was already in the database, {copies} copies were added to it", color=discord.Color.green())
        else:
            embed = discord.Embed(title="Book inserted", description=f"Book {name} inserted successfully", color=discord.Color.green())
        view = DetailsView(interaction.user.id, ObjectType.BOOK, itemID, self.applyDetails)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @staticmethod
    def parseEnum(value: str, enumClass) -> tuple[bool, int | None]:
        text = value.strip().upper()
        if text == "":
            return True, None
        if text in enumClass.__members__:
            return True, enumClass[text].value
        return False, None

    @staticmethod
    def applyDetailsEmbed(itemType: ObjectType, itemID: int, modal: DetailsModal) -> discord.Embed:
        label = ITEM_LABELS[itemType]
        values = {"description": modal.description.component.value, "thumbnail": modal.thumbnail.component.value}
        for name, enumClass in DETAIL_ENUMS.items():
            if not hasattr(modal, name):
                continue
            valid, value = GamesCog.parseEnum(getattr(modal, name).component.value, enumClass)
            if not valid:
                choices = ", ".join(member.name.lower() for member in enumClass)
                return discord.Embed(title=f"Error updating {label.lower()}", description=f"{getattr(modal, name).text} must be one of: {choices}", color=discord.Color.red())
            if value is not None:
                values[name] = value
        return GamesCog.applyEdit(itemType, str(itemID), label, values, modal.categories.component.value)

    async def applyDetails(self, itemType: ObjectType, itemID: int, interaction: discord.Interaction, modal: DetailsModal):
        await interaction.response.send_message(embed=GamesCog.applyDetailsEmbed(itemType, itemID, modal), ephemeral=True)

    @app_commands.command(name="editbg", description="Update a boardgame that is already in the database")
    @app_commands.describe(item="Boardgame to update", name="New name of the boardgame",
                           description="New description, pass a single space to restore the default one",
                           thumbnail="New cover image URL, pass a single space to restore the default one",
                           categories="New comma separated list of categories, pass a single space to remove all of them",
                           copies="New number of copies", min_players="New minimum number of players",
                           max_players="New maximum number of players", length="New playing time in minutes",
                           play_difficulty="New difficulty of playing the game", learn_difficulty="New difficulty of learning the game")
    @app_commands.choices(play_difficulty=DIFFICULTY_CHOICES, learn_difficulty=DIFFICULTY_CHOICES)
    @app_commands.autocomplete(item=boardgameAutocomplete)
    async def editBoardgame(self, interaction: discord.Interaction, item: str, name: str = None, description: str = None, thumbnail: str = None,
                            categories: str = None, copies: int = None, min_players: int = None, max_players: int = None, length: int = None,
                            play_difficulty: str = None, learn_difficulty: str = None):
        await interaction.response.defer()
        embed = GamesCog.applyEdit(ObjectType.BOARDGAME, item, ITEM_LABELS[ObjectType.BOARDGAME], {
            "name": name, "description": description, "thumbnail": thumbnail, "copies": copies, "min_players": min_players,
            "max_players": max_players, "length": length,
            "play_difficulty": Difficulty[play_difficulty.upper()].value if play_difficulty is not None else None,
            "learn_difficulty": Difficulty[learn_difficulty.upper()].value if learn_difficulty is not None else None
        }, categories)
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="editvg", description="Update a videogame that is already in the database")
    @app_commands.describe(item="Videogame to update", name="New name of the videogame",
                           description="New description, pass a single space to restore the default one",
                           thumbnail="New cover image URL, pass a single space to restore the default one",
                           categories="New comma separated list of categories, pass a single space to remove all of them",
                           copies="New number of copies", min_players="New minimum number of players",
                           max_players="New maximum number of players", length="New length in minutes",
                           platform="New platform of the videogame", difficulty="New difficulty of the videogame")
    @app_commands.choices(platform=PLATFORM_CHOICES, difficulty=DIFFICULTY_CHOICES)
    @app_commands.autocomplete(item=videogameAutocomplete)
    async def editVideogame(self, interaction: discord.Interaction, item: str, name: str = None, description: str = None, thumbnail: str = None,
                            categories: str = None, copies: int = None, min_players: int = None, max_players: int = None, length: int = None,
                            platform: str = None, difficulty: str = None):
        await interaction.response.defer()
        embed = GamesCog.applyEdit(ObjectType.VIDEOGAME, item, ITEM_LABELS[ObjectType.VIDEOGAME], {
            "name": name, "description": description, "thumbnail": thumbnail, "copies": copies, "min_players": min_players,
            "max_players": max_players, "length": length,
            "platform": Platform[platform.upper()].value if platform is not None else None,
            "difficulty": Difficulty[difficulty.upper()].value if difficulty is not None else None
        }, categories)
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="editbook", description="Update a book that is already in the database")
    @app_commands.describe(item="Book to update", name="New title of the book", author="New author of the book",
                           description="New description, pass a single space to restore the default one",
                           thumbnail="New cover image URL, pass a single space to restore the default one",
                           categories="New comma separated list of categories, pass a single space to remove all of them",
                           copies="New number of copies", pages="New number of pages")
    @app_commands.autocomplete(item=bookAutocomplete)
    async def editBook(self, interaction: discord.Interaction, item: str, name: str = None, author: str = None, description: str = None,
                       thumbnail: str = None, categories: str = None, copies: int = None, pages: int = None):
        await interaction.response.defer()
        embed = GamesCog.applyEdit(ObjectType.BOOK, item, ITEM_LABELS[ObjectType.BOOK], {
            "name": name, "author": author, "description": description, "thumbnail": thumbnail, "copies": copies, "length": pages
        }, categories)
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="deleteitem", description="Delete an item from the database")
    @app_commands.describe(item="Item to delete")
    @app_commands.autocomplete(item=itemAutocomplete)
    async def deleteItem(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer()
        itemID = DBManager.getInstance().getItemIDFromName(item)
        itemType = None if itemID == -1 else DBManager.getInstance().getItemType(itemID)
        if itemType is None:
            embed = discord.Embed(title="Error deleting item", description="Item not found", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        name = DBManager.getInstance().getItemNameFromID(itemID)
        usage = DBManager.getInstance().getItemUsage(itemID)
        if usage['borrowed'] > 0:
            embed = discord.Embed(title="Error deleting item", color=discord.Color.red(),
                                  description=f"**{name}** cannot be deleted while {usage['borrowed']} of its copies are borrowed")
            await interaction.edit_original_response(embed=embed)
            return
        embed = discord.Embed(title="Confirm deletion", color=discord.Color.orange(),
                              description=f"Delete **{name}** ({ITEM_LABELS[itemType]})?\n"
                                          f"Its {usage['borrows']} borrow records and {usage['interests']} interests will be deleted as well")
        view = ConfirmView(interaction.user.id, embed, partial(GamesCog.deleteItemConfirmed, itemID), "Delete", "Cancel")
        view.message = await interaction.original_response()
        await interaction.edit_original_response(embed=embed, view=view)

    @staticmethod
    def deleteItemConfirmed(itemID: int) -> discord.Embed:
        success, message = DBManager.getInstance().deleteItem(itemID)
        if not success:
            return discord.Embed(title="Error deleting item", description=message, color=discord.Color.red())
        return discord.Embed(title="Item deleted", description=message, color=discord.Color.green())

    @staticmethod
    def resolveItem(itemType: ObjectType, item: str) -> tuple[int, object] | None:
        itemID = int(item) if item.isdigit() else DBManager.getInstance().getItemIDFromName(item)
        if itemID == -1:
            return None
        entry = DBManager.getInstance().getItemData(itemType, itemID)
        return None if entry is None else (itemID, entry)

    @staticmethod
    def applyEdit(itemType: ObjectType, item: str, label: str, values: dict, categories: str = None) -> discord.Embed:
        resolved = GamesCog.resolveItem(itemType, item)
        if resolved is None:
            return discord.Embed(title=f"Error updating {label.lower()}", description=f"{label} not found", color=discord.Color.red())
        itemID, entry = resolved
        changes = {key: value for key, value in values.items() if value is not None}
        if "name" in changes:
            name = changes["name"].strip()
            if name == "":
                del changes["name"]
            else:
                changes["name"] = name
        if "description" in changes:
            changes["description"] = changes["description"].strip() or DEFAULT_DESCRIPTION
        if "thumbnail" in changes:
            changes["thumbnail"] = changes["thumbnail"].strip() or DEFAULT_THUMBNAIL
        for key in ("copies", "min_players", "max_players", "length"):
            if key in changes and changes[key] < 0:
                return discord.Embed(title=f"Error updating {label.lower()}", description=f"{key.replace('_', ' ').capitalize()} cannot be negative", color=discord.Color.red())
        if "copies" in changes and changes["copies"] < entry.copies - entry.copies_available:
            borrowed = entry.copies - entry.copies_available
            return discord.Embed(title=f"Error updating {label.lower()}", description=f"There are {borrowed} copies currently borrowed, so there cannot be fewer than {borrowed} copies", color=discord.Color.red())
        categoryList = None
        if categories is not None:
            categoryList = list(dict.fromkeys(category.strip() for category in categories.split(",") if category.strip() != ""))
        if len(changes) == 0 and categoryList is None:
            embed = entry.getEmbed([])
            embed.set_footer(text="Nothing was updated, these are the current values")
            return embed
        if not DBManager.getInstance().updateItem(itemType, itemID, changes):
            description = f"An item named '{changes['name']}' already exists" if "name" in changes else "The update could not be applied"
            return discord.Embed(title=f"Error updating {label.lower()}", description=description, color=discord.Color.red())
        if categoryList is not None:
            DBManager.getInstance().setCategories(itemID, categoryList)
        return discord.Embed(title=f"{label} updated", description=f"{label} updated successfully", color=discord.Color.green())

    @app_commands.command(name="bgsearch", description="Simple command to get the list of boardgames with some filters")
    @app_commands.describe(name="Only show boardgames whose name contains this", max_difficulty="Only show boardgames at most this hard to play",
                           player_count="Only show boardgames that support this many players", max_length="Only show boardgames at most this long",
                           compact="Show a compact version of the embeds", all_categories="Show every category instead of the first three", private="Only show the result to you")
    @app_commands.choices(max_difficulty=DIFFICULTY_CHOICES)
    @app_commands.autocomplete(name=boardgameNameAutocomplete)
    async def getBoardgames(self, interaction: discord.Interaction, name: str = "", max_difficulty: str = "", player_count: int = 0, max_length: int = 0,
                            compact: bool = False, all_categories: bool = False, private: bool = True):
        await interaction.response.defer(ephemeral=private)
        filters: list[tuple[str, Operation, object]] = []
        if name:
            filters.append(("name", Operation.Equal, name))
        if max_difficulty:
            filters.append(("play_difficulty", Operation.LessOrEqual, Difficulty[max_difficulty.upper()].value))
        if player_count > 0:
            filters.append(("max_players", Operation.GreaterOrEqual, player_count))
            filters.append(("min_players", Operation.LessOrEqual, player_count))
        if max_length > 0:
            filters.append(("length", Operation.LessOrEqual, max_length))
        games: list = DBManager.getInstance().getFilteredList(ObjectType.BOARDGAME, filters)
        if len(games) == 0:
            embed: discord.Embed = discord.Embed(title="No boardgames found", description="No boardgames found with the specified filters", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        await GamesCog._sendQueryEmbed(interaction, games, compact, all_categories)

    @app_commands.command(name="vgsearch", description="Simple command to get the list of videogames with some filters")
    @app_commands.describe(name="Only show videogames whose name contains this", max_difficulty="Only show videogames at most this hard",
                           player_count="Only show videogames that support this many players", platform="Only show videogames of this platform",
                           compact="Show a compact version of the embeds", all_categories="Show every category instead of the first three", private="Only show the result to you")
    @app_commands.choices(max_difficulty=DIFFICULTY_CHOICES, platform=PLATFORM_CHOICES)
    @app_commands.autocomplete(name=videogameNameAutocomplete)
    async def getVideogames(self, interaction: discord.Interaction, name: str = "", max_difficulty: str = "", player_count: int = 0, platform: str = "",
                            compact: bool = False, all_categories: bool = False, private: bool = True):
        await interaction.response.defer(ephemeral=private)
        filters: list[tuple[str, Operation, object]] = []
        if name:
            filters.append(("name", Operation.Equal, name))
        if max_difficulty:
            filters.append(("difficulty", Operation.LessOrEqual, Difficulty[max_difficulty.upper()].value))
        if player_count > 0:
            filters.append(("max_players", Operation.GreaterOrEqual, player_count))
            filters.append(("min_players", Operation.LessOrEqual, player_count))
        if platform:
            filters.append(("platform", Operation.Equal, Platform[platform.upper()].value))
        games: list = DBManager.getInstance().getFilteredList(ObjectType.VIDEOGAME, filters)
        if len(games) == 0:
            embed: discord.Embed = discord.Embed(title="No videogames found", description="No videogames found with the specified filters", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        await GamesCog._sendQueryEmbed(interaction, games, compact, all_categories)

    @app_commands.command(name="booksearch", description="Simple command to get the list of books with some filters")
    @app_commands.describe(name="Only show books whose name contains this", author="Only show books by this author", min_pages="Only show books at least this long",
                           compact="Show a compact version of the embeds", all_categories="Show every category instead of the first three", private="Only show the result to you")
    @app_commands.autocomplete(name=bookNameAutocomplete, author=bookAuthorAutocomplete)
    async def getBooks(self, interaction: discord.Interaction, name: str = "", author: str = "", min_pages: int = 0, compact: bool = False,
                       all_categories: bool = False, private: bool = True):
        await interaction.response.defer(ephemeral=private)
        filters: list[tuple[str, Operation, object]] = []
        if name:
            filters.append(("name", Operation.Equal, name))
        if author:
            filters.append(("author", Operation.Equal, author))
        if min_pages > 0:
            filters.append(("length", Operation.GreaterOrEqual, min_pages))
        books: list = DBManager.getInstance().getFilteredList(ObjectType.BOOK, filters)
        if len(books) == 0:
            embed: discord.Embed = discord.Embed(title="No books found", description="No books found with the specified filters", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        await GamesCog._sendQueryEmbed(interaction, books, compact, all_categories)

    @app_commands.command(name="interest", description="Declare interest in borrowing an item from Piazza")
    @app_commands.describe(item="Item you are interested in")
    @app_commands.autocomplete(item=itemAutocomplete)
    async def declareInterest(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer()
        itemID = DBManager.getInstance().getItemIDFromName(item)
        if itemID == -1:
            embed = discord.Embed(title="Error declaring interest", description="Item not found", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        data = DBManager.getInstance().getBorrowsList(interaction.user.id, itemID, True)
        success = DBManager.getInstance().declareInterest(interaction.user.id, itemID)
        if not success:
            embed = discord.Embed(title="Error declaring interest", description="You have already declared interest for this item", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        embed = discord.Embed(
            title=f"Someone declared interest for the game {DBManager.getInstance().getItemNameFromID(itemID)}",
            description="Don't worry! This does not mean you have to return it right away. It just means someone wants to borrow it too. Just make sure to return it as soon as you are done with it!",
            color=discord.Color.orange())
        for entry in data:
            user = await fetchUser(self.bot, entry['user'])
            if user is None or user.id == interaction.user.id:
                continue
            await sendDirectMessage(user, embed)
        embed = discord.Embed(title="Interest declared successfully", description="You will be notified when someone returns or borrows the game", color=discord.Color.green())
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="uninterest", description="Cancel interest in borrowing an item from Piazza")
    @app_commands.describe(item="Item you want to cancel your interest in")
    @app_commands.autocomplete(item=interestAutocomplete)
    async def cancelInterest(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer()
        itemID = DBManager.getInstance().getItemIDFromName(item)
        if itemID == -1:
            embed = discord.Embed(title="Error cancelling interest", description="Item not found", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        success = DBManager.getInstance().cancelInterest(interaction.user.id, itemID)
        if not success:
            embed = discord.Embed(title="Error cancelling interest", description="You have not declared interest for this item", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        embed = discord.Embed(
            title=f"Cancelled interest successfully",
            description=f"You will no longer be notified when someone returns or borows the game {DBManager.getInstance().getItemNameFromID(itemID)}",
            color=discord.Color.orange())
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="borrow", description="Borrow something from Piazza. Dates should be written in the format YYYY-MM-DD")
    @app_commands.describe(item="Item you want to borrow", planned_return="Date you plan to return it", retrieval_date="Date you retrieved it")
    @app_commands.autocomplete(item=borrowableAutocomplete)
    async def borrowItem(self, interaction: discord.Interaction, item: str, planned_return: str = None, retrieval_date: str = None):
        await interaction.response.defer()
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
            itemIDs = [entry['id'] for entry in DBManager.getInstance().getItemsToBorrowFromName(interaction.user.id, item)]
            if len(itemIDs) == 0:
                success = False
                if len(DBManager.getInstance().getItemsToReturnFromName(interaction.user.id, item)) > 0:
                    message = "You are already borrowing this item"
                elif DBManager.getInstance().getItemIDFromName(item) != -1:
                    message = "There are no copies left of this item in Piazza"
                else:
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
                success, message = DBManager.getInstance().borrowItem(interaction.user.id, itemID, planned_return, retrieval_date)
        if success:
            data = DBManager.getInstance().getInterested(itemID)
            availableCopies = DBManager.getInstance().getItemAvailableCopies(itemID)
            if availableCopies == 0:
                description = "There are no available copies of this game at the moment. You will be notified when someone returns it."
            else:
                description = f"There are still {availableCopies} available copies of this game."
            dmEmbed = discord.Embed(title=f"Someone borrowed the game {DBManager.getInstance().getItemNameFromID(itemID)}", description=description, color=discord.Color.orange() if availableCopies == 0 else discord.Color.yellow())
            removedInterest = False
            for entry in data:
                if entry['user'] == interaction.user.id:
                    DBManager.getInstance().cancelInterest(entry['user'], itemID)
                    removedInterest = True
                    continue
                user = await fetchUser(self.bot, entry['user'])
                if user is not None:
                    await sendDirectMessage(user, dmEmbed)
            if removedInterest:
                message += "\nYou have been removed from the interest list for this game."
            embed: discord.Embed = discord.Embed(title="Item borrowed", description=message, color=discord.Color.green())
        else:
            embed: discord.Embed = discord.Embed(title="Error borrowing item", description=message, color=discord.Color.red())
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="returnall", description="Return all items you borrowed from Piazza")
    async def returnAllItems(self, interaction: discord.Interaction):
        await interaction.response.defer()
        amount = DBManager.getInstance().getBorrowsAmount(interaction.user.id, True)
        if amount == 0:
            embed = discord.Embed(title="Error returning items", description="You have not borrowed any items from Piazza", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        embed = discord.Embed(title="Confirm return", description=f"Return all {amount} items you borrowed from Piazza?", color=discord.Color.orange())
        view = ConfirmView(interaction.user.id, embed, partial(GamesCog.returnAll, interaction.client, interaction.user.id), "Return all", "Cancel")
        view.message = await interaction.original_response()
        await interaction.edit_original_response(embed=embed, view=view)

    @staticmethod
    async def returnAll(bot: discord.Client, user: int) -> discord.Embed:
        items = DBManager.getInstance().getBorrowsList(user, None, True)
        success, message = DBManager.getInstance().returnAllItems(user)
        if not success:
            return discord.Embed(title="Error returning items", description=message, color=discord.Color.red())
        for entry in items:
            availableCopies = DBManager.getInstance().getItemAvailableCopies(entry['id'])
            description = f"There are {availableCopies} available copies of this game."
            dmEmbed = discord.Embed(title=f"Someone returned the game {entry['name']}", description=description, color=discord.Color.green())
            for interest in DBManager.getInstance().getInterested(entry['id']):
                interestedUser = await fetchUser(bot, interest['user'])
                if interestedUser is not None:
                    await sendDirectMessage(interestedUser, dmEmbed)
        return discord.Embed(title="Items returned", description=message, color=discord.Color.green())

    @app_commands.command(name="return", description="Return something you borrowed to Piazza")
    @app_commands.describe(item="Item you want to return")
    @app_commands.autocomplete(item=returnableAutocomplete)
    async def returnItem(self, interaction: discord.Interaction, item: str):
        await interaction.response.defer()
        itemIDs = [entry['id'] for entry in DBManager.getInstance().getItemsToReturnFromName(interaction.user.id, item)]
        if len(itemIDs) == 0:
            embed = discord.Embed(title="Error returning item", description="Item not found", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        elif len(itemIDs) > 1:
            gameNames = ["- " + DBManager.getInstance().getItemNameFromID(entry) for entry in itemIDs]
            if len(gameNames) > 15:
                gameList = "\n".join(gameNames[:15]) + f"\n(+{len(gameNames) - 15})"
            else:
                gameList = "\n".join(gameNames)
            embed = discord.Embed(title="Error returning item", description="**Multiple items found:**\n" + gameList + "\n\n**Please be more specific.**", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        else:
            itemID = itemIDs[0]
            success, message = DBManager.getInstance().returnItem(interaction.user.id, itemID)
        if not success:
            embed = discord.Embed(title="Error returning item", description=message, color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        embed = discord.Embed(title="Item returned", description=message, color=discord.Color.green())
        await interaction.edit_original_response(embed=embed)
        data = DBManager.getInstance().getInterested(itemID)
        availableCopies = DBManager.getInstance().getItemAvailableCopies(itemID)
        description = f"There are {availableCopies} available copies of this game."
        dmEmbed = discord.Embed(title=f"Someone returned the game {DBManager.getInstance().getItemNameFromID(itemID)}", description=description, color=discord.Color.green())
        for entry in data:
            user = await fetchUser(self.bot, entry['user'])
            if user is not None:
                await sendDirectMessage(user, dmEmbed)

    @staticmethod
    async def execGetBorrowsCommand(interaction: discord.Interaction, current: bool, user: discord.Member = None, private: bool = True):
        await interaction.response.defer(ephemeral=private)
        userID = user.id if user is not None else None
        total = DBManager.getInstance().getBorrowsAmount(userID, current)
        if total == 0:
            titleAppend = (" by " + (user.nick if user.nick is not None else user.name)) if user is not None else ""
            embed: discord.Embed = discord.Embed(title="Items borrowed" + titleAppend, description="No items have been borrowed from Piazza" + titleAppend, color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        pages = countPages(total)

        async def loadPage(page: int) -> discord.Embed:
            items = DBManager.getInstance().getBorrowsList(userID, None, current, PAGE_SIZE, page * PAGE_SIZE)
            users = await fetchUsers(interaction.client, [item['user'] for item in items])
            for item in items:
                item['user'] = mention(users.get(item['user'], item['user']))
            embed = getBorrowsListEmbed(items, user, current)
            embed.set_footer(text=f"page {page + 1} of {pages}")
            return embed

        view = LazyPaginator(pages, loadPage)
        view.message = await interaction.original_response()
        await interaction.edit_original_response(embed=await loadPage(0), view=view)

    @app_commands.command(name="getborrows", description="Get the list of items borrowed from Piazza")
    @app_commands.describe(user="Only show the items borrowed by this user", private="Only show the result to you")
    async def getBorrows(self, interaction: discord.Interaction, user: discord.Member = None, private: bool = True):
        await GamesCog.execGetBorrowsCommand(interaction, True, user, private)

    @app_commands.command(name="getborrowhistory", description="Get the history of borrowed items from Piazza")
    @app_commands.describe(user="Only show the items borrowed by this user", private="Only show the result to you")
    async def getBorrowHistory(self, interaction: discord.Interaction, user: discord.Member = None, private: bool = True):
        await GamesCog.execGetBorrowsCommand(interaction, False, user, private)

    @app_commands.command(name="getborrowstats", description="Get the borrow highscores!")
    @app_commands.describe(order="What to rank by", target="Rank users or items", private="Only show the result to you")
    @app_commands.choices(order=BORROW_ORDER_CHOICES, target=BORROW_TARGET_CHOICES)
    async def getBorrowStats(self, interaction: discord.Interaction, order: str = "amount", target: str = "user", private: bool = True):
        await interaction.response.defer(ephemeral=private)
        if target == "user":
            if order not in ["time", "amount", "count", "current"]:
                order = "total"
        else:
            if order not in ["time", "amount", "count", "usertime"]:
                order = "total"
        if order in ["amount", "count"]:
            order = "total"
        total = DBManager.getInstance().getBorrowStatsCount(target)
        if total == 0:
            embed = discord.Embed(title="No borrow stats retrieved", description="Either this is a very weird error or no one has borrowed anything yet", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        pages = countPages(total)

        async def loadPage(page: int) -> discord.Embed:
            entries = DBManager.getInstance().getBorrowStats(order, target, PAGE_SIZE, page * PAGE_SIZE)
            users = await fetchUsers(interaction.client, [entry['user'] for entry in entries])
            for index, entry in enumerate(entries):
                entry['rank'] = page * PAGE_SIZE + index + 1
                entry['user'] = users.get(entry['user'], entry['user'])
            embed = getBorrowsStatsEmbed(entries, order) if target == "user" else getBorrowsItemStatsEmbed(entries, order)
            embed.set_footer(text=f"page {page + 1} of {pages}")
            return embed

        view = LazyPaginator(pages, loadPage)
        view.message = await interaction.original_response()
        await interaction.edit_original_response(embed=await loadPage(0), view=view)

    @staticmethod
    async def _sendQueryEmbed(interaction: discord.Interaction, items: list, compact: bool, all_categories: bool):
        flags = (["compact"] if compact else []) + (["allCats"] if all_categories else [])
        embed = items[0].getEmbed(flags)
        view = ItemPaginator(items, flags, embed)
        embed.set_footer(text="Use arrows to move between pages")
        view.message = await interaction.original_response()
        await interaction.edit_original_response(embed=embed, view=view)
