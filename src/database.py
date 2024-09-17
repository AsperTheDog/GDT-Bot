import os
import sqlite3 as SQLite
import csv
from datetime import datetime

from enum import Enum
from typing import Any, Tuple

from disnake import Embed, Color, ApplicationCommandInteraction, Member


class Difficulty(Enum):
    UNDEFINED = 0
    PARTY = 1
    EASY = 2
    NORMAL = 3
    HARD = 4
    CAMPAIGN = 5


class Platform(Enum):
    UNDEFINED = 0
    PC = 1
    PS4 = 2
    PS5 = 3
    XBOX = 4
    SWITCH = 5


class Operation(Enum):
    Equal = "=="
    NotEqual = "!="
    Greater = ">"
    Less = "<"
    GreaterOrEqual = ">="
    LessOrEqual = "<="


class ObjectType(Enum):
    BOARDGAME = "boardgames"
    VIDEOGAME = "videogames"
    BOOK = "books"


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
        if col[0] in ["play_difficulty", "learn_difficulty", "difficulty"]:
            d[col[0]] = Difficulty(d[col[0]])
        if col[0] == "platform":
            d[col[0]] = Platform(d[col[0]])
        if col[0] == "type":
            d[col[0]] = ObjectType(d[col[0]] + "s")
        if col[0] == "returned" or col[0] == "planned_return" or col[0] == "retrieval_date" or col[0] == "register_date":
            if d[col[0]] is not None:
                d[col[0]] = datetime.strptime(d[col[0]], "%Y-%m-%d %H:%M:%S.%f")
            else:
                d[col[0]] = None
    return d


class DatabaseManager:
    def __init__(self, database: str):
        self.path: str = database
        self.connection: SQLite.Connection = self._createDatabase(not os.path.exists(database))
        self.connection.row_factory = dict_factory
        print("Database connection established")

    def __del__(self):
        print("Closing database connection...")
        self.connection.close()

    def _createDatabase(self, hardReset: bool = False) -> SQLite.Connection:
        print("Initializing database...")
        if hardReset and os.path.exists(self.path):
            os.remove(self.path)
        connection: SQLite.Connection = SQLite.connect(self.path)
        cursor: SQLite.Cursor = connection.cursor()

        with open("data_files/queries/generateDB.sql", 'r') as data:
            cursor.executescript(data.read())

        if hardReset:
            print("Populating default data...")
            for file, table in {"data_files/boardgames.csv": "boardgames",
                                "data_files/videogames.csv": "videogames"}.items():
                with open(file, 'r') as data:
                    dr = csv.DictReader(data)
                    for entry in dr:
                        itemData = {"type": table[:-1]}
                        specificData = {"id": None}
                        for key, value in entry.items():
                            if key in ["name", "copies"]:
                                itemData[key] = value
                            else:
                                specificData[key] = value
                        cursor.execute(f"INSERT INTO items ({', '.join(itemData.keys())}) VALUES ({', '.join(['?' for _ in itemData.keys()])})", list(itemData.values()))
                        cursor.execute(f"SELECT id FROM items WHERE name = ?", (itemData['name'],))
                        specificData['id'] = cursor.fetchone()[0]
                        cursor.execute(f"INSERT INTO {table} ({', '.join(specificData.keys())}) VALUES ({', '.join(['?' for _ in specificData.keys()])})", list(specificData.values()))

        connection.commit()
        return connection

    def getItemIDFromName(self, name: str) -> int:
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM items WHERE name = ?", (name,))
        data = cursor.fetchone()
        return data['id'] if data is not None else -1

    def getFilteredList(self, itemType: ObjectType, orFilters: str, andFilters: str, ascending: bool = False, limit: int = 0, offset: int = 0) -> [dict]:
        orFilterData = self._parseFilterTokens(orFilters)
        andFilterData = self._parseFilterTokens(andFilters)
        with open("data_files/queries/getFilteredList.sql", 'r') as data:
            query = data.read().format(itemType.value)
        cursor = self.connection.cursor()
        queries = []
        arguments = [itemType.value[:-1]]
        if len(orFilterData) > 0 or len(andFilterData) > 0:
            query += f" WHERE "
        for filterToken in orFilterData:
            queryFragment, arg = self._parseToQuery(filterToken)
            queries.append(queryFragment)
            arguments.append(arg)
        query += f" OR ".join(queries)
        if len(orFilterData) > 0:
            query += f" AND "
        queries = []
        for filterToken in andFilterData:
            queryFragment, arg = self._parseToQuery(filterToken)
            queries.append(queryFragment)
            arguments.append(arg)
        query += f" AND ".join(queries)
        if ascending:
            query += " ORDER BY name ASC "
        if limit > 0:
            query += f" LIMIT ? "
            arguments.append(limit)
            if offset > 0:
                query += f" OFFSET ? "
                arguments.append(offset)
        cursor.execute(query, arguments)
        return cursor.fetchall()

    def getItemEmbed(self, itemType: ObjectType, itemID: int, extended: bool) -> Embed | None:
        def getBoardgameEmbed(data: dict) -> Embed:
            color: Color = Color.dark_green() if data['copies_left'] > 0 else Color.red()
            embed = Embed(title=data['name'] + (f" ({itemID})" if not extended else ""), color=color)
            if extended:
                embed.add_field(name="ID", value=data['id'], inline=False)
            embed.add_field(name="Players", value=f"{data['min_players']} - {data['max_players']}", inline=False)
            if not extended:
                embed.add_field(name="Difficulty", value=f"Play: {data['play_difficulty'].name.lower()} - Learn: {data['learn_difficulty'].name.lower()}", inline=False)
            else:
                embed.add_field(name="Play difficulty", value=f"{data['play_difficulty'].name.lower()}")
                embed.add_field(name="Learn difficulty", value=f"{data['learn_difficulty'].name.lower()}")
            embed.add_field(name="Length", value=f"{data['length']} minutes", inline=False)
            embed.add_field(name="Copies in Piazza", value=data['copies_left'])
            if extended:
                embed.add_field(name="Total copies", value=data['copies'])
            return embed

        def getVideogameEmbed(data: dict) -> Embed:
            color: Color = Color.dark_green() if data['copies_left'] > 0 else Color.red()
            embed = Embed(title=data['name'] + (f" ({itemID})" if not extended else ""), color=color)
            if extended:
                embed.add_field(name="ID", value=data['id'], inline=False)
            embed.add_field(name="Players", value=f"{data['min_players']} - {data['max_players']}", inline=False)
            embed.add_field(name="Difficulty", value=f"{data['difficulty'].name.lower()}", inline=False)
            embed.add_field(name="Length", value=f"{data['length']} minutes", inline=False)
            embed.add_field(name="Platform", value=f"{data['platform'].name.lower()}", inline=False)
            embed.add_field(name="Copies in Piazza", value=data['copies_left'])
            if extended:
                embed.add_field(name="Total copies", value=data['copies'])
            return embed

        def getBookEmbed(data: dict) -> Embed:
            color: Color = Color.dark_green() if data['copies_left'] > 0 else Color.red()
            embed = Embed(title=data['name'] + (f" ({itemID})" if not extended else ""), color=color)
            if extended:
                embed.add_field(name="ID", value=data['id'], inline=False)
            embed.add_field(name="Author", value=data['author'], inline=False)
            embed.add_field(name="Pages", value=data['pages'], inline=False)
            embed.add_field(name="Genre", value=data['genre'], inline=False)
            embed.add_field(name="Copies in Piazza", value=data['copies_left'])
            if extended:
                embed.add_field(name="Total copies", value=data['copies'])
                embed.add_field(name="Abstract", value=data['abstract'], inline=False)
            return embed

        cursor = self.connection.cursor()
        with open("data_files/queries/getItem.sql", 'r') as data:
            cursor.execute(data.read().format(itemType.value), (itemType.value[:-1], itemID))
        queryResult = cursor.fetchone()
        if queryResult is None:
            return None
        if itemType.value == ObjectType.BOARDGAME.value:
            return getBoardgameEmbed(queryResult)
        elif itemType.value == ObjectType.VIDEOGAME.value:
            return getVideogameEmbed(queryResult)
        else:
            return getBookEmbed(queryResult)

    async def getBorrowsListEmbed(self, pageRange: (int, int), inter: ApplicationCommandInteraction, user: int = None, current: bool = True) -> Embed:
        cursor = self.connection.cursor()
        with open("data_files/queries/getMixedList.sql", 'r') as data:
            query = data.read()
        userFilter = "WHERE user = ?" if user is not None else ""
        returnFilter = ("WHERE" if userFilter == "" else "AND") + f" returned IS {"" if current else "NOT"} NULL"
        pageFilter = f" LIMIT {pageRange[1] - pageRange[0]}" + (f" OFFSET {pageRange[0]}" if pageRange[0] > 0 else "")
        finalFilter = userFilter + returnFilter + pageFilter
        if userFilter == "":
            cursor.execute(query.format(finalFilter))
        else:
            cursor.execute(query.format(finalFilter), (user,))
        data = cursor.fetchall()
        if user is not None:
            user: Member = (await inter.guild.fetch_member(user))
            titleAppend: str = " by " + (user.nick if user.nick is not None else user.name)
        else:
            titleAppend = ""
        embed = Embed(title="Items borrowed" + titleAppend, color=Color.dark_gold())
        embed.add_field(name="User", value="\n".join([(await inter.guild.fetch_member(entry['user'])).mention for entry in data]), inline=True)
        embed.add_field(name="Item (type)", value="\n".join([str(entry['name']) + f" ({entry['type'].value[:-1]})" for entry in data]), inline=True)
        if current:
            embed.add_field(name="Copies left", value="\n".join([str(entry['available_copies']) for entry in data]), inline=True)
        else:
            embed.add_field(name="Returned", value="\n".join([entry['returned'].strftime("%d/%m/%Y") for entry in data]), inline=True)
        return embed

    def getBorrowsAmount(self, user: int, current: bool) -> int:
        cursor = self.connection.cursor()
        if user is None:
            cursor.execute(f"SELECT COUNT(*) AS amount FROM borrows WHERE returned IS {"" if current else "NOT"} NULL")
        else:
            cursor.execute(f"SELECT COUNT(*) AS amount FROM borrows WHERE user = ? AND returned IS {"" if current else "NOT"} NULL", (user,))
        return cursor.fetchone()['amount']

    def getReminders(self) -> [dict]:
        cursor = self.connection.cursor()
        with open("data_files/queries/getReminders.sql", 'r') as data:
            cursor.execute(data.read())
        return cursor.fetchall()

    def returnItem(self, user: int, item: str) -> (bool, str):
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM items WHERE id = ?) AS item_exists", (item,))
        if not cursor.fetchone()['item_exists']:
            return False, "This item does not exist"

        # Check the user has not borrowed the item already
        cursor.execute("SELECT EXISTS(SELECT 1 FROM borrows WHERE user = ? AND item = ? AND returned IS NULL) AS already_borrowed", (user, item))
        if not cursor.fetchone()['already_borrowed']:
            return False, "You are not borrwing this item"

        cursor.execute("UPDATE borrows SET returned = ? WHERE user = ? AND item = ? AND returned IS NULL", (datetime.now(), user, item))
        self.connection.commit()

        cursor.execute("SELECT name FROM items WHERE id = ?", (item,))
        item_name = cursor.fetchone()['name']

        return True, f"Item '{item_name}' returned successfully"

    def setReminderSent(self, user: int) -> bool:
        cursor = self.connection.cursor()
        cursor.execute("UPDATE users SET reminded = TRUE WHERE user = ?", (user,))
        self.connection.commit()
        return True

    # TODO: Make method take data from BGG
    def insertBoardgame(self, bggCode: int, name: str, play_difficulty: Difficulty, learn_difficulty: Difficulty, min_players: int, max_players: int, length: int, copies: int) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute("INSERT INTO items (name, type, copies) VALUES (?)", (name, "boardgame", copies))
            cursor.execute("SELECT id FROM items WHERE name = ?", (name,))
            itemID = cursor.fetchone()['id']
            cursor.execute("INSERT INTO boardgames (id, bgg_id, play_difficulty, learn_difficulty, min_players, max_players, length) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (itemID, bggCode, play_difficulty.value, learn_difficulty.value, min_players, max_players, length))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

    def deleteBoardgame(self, id: int) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute("DELETE FROM items WHERE id = ?", (id,))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

    def insertVideogame(self, name: str, platform: Platform, difficulty: Difficulty, min_players: int, max_players: int, length: int, copies: int) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute("INSERT INTO items (name, type, copies) VALUES (?)", (name, "videogame", copies))
            cursor.execute("SELECT id FROM items WHERE name = ?", (name,))
            itemID = cursor.fetchone()['id']
            cursor.execute("INSERT INTO videogames (id, platform, difficulty, min_players, max_players, length) VALUES (?, ?, ?, ?, ?, ?)",
                           (itemID, platform.value, difficulty.value, min_players, max_players, length))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

    def deleteVideogame(self, id: int) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute("DELETE FROM items WHERE id = ?", (id,))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

    def insertBook(self, name: str, author: str, pages: int, genre: str, abstract: str, copies: int) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute("INSERT INTO items (name, type, copies) VALUES (?)", (name, "book", copies))
            cursor.execute("SELECT id FROM items WHERE name = ?", (name,))
            itemID = cursor.fetchone()['id']
            cursor.execute("INSERT INTO books (id, author, pages, genre, abstract) VALUES (?, ?, ?, ?, ?)",
                           (itemID, author, pages, genre, abstract))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

    def deleteBook(self, id: int) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute("DELETE FROM items WHERE id = ?", (id,))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

    def editCopies(self, itemID: int, copies: int) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute(f"UPDATE items SET copies = ? WHERE id = ?", (copies, itemID))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

    def borrowItem(self, user: int, item: int, planned_return: datetime, retrieval_date: datetime) -> (bool, str):
        cursor = self.connection.cursor()
        # Check the item exists
        cursor.execute("SELECT EXISTS(SELECT 1 FROM items WHERE id = ?) AS item_exists", (item,))
        if not cursor.fetchone()['item_exists']:
            return False, "This item does not exist"

        # Check the user has not borrowed the item already
        cursor.execute("SELECT EXISTS(SELECT 1 FROM borrows WHERE user = ? AND item = ? AND returned IS NULL) AS already_borrowed", (user, item))
        if cursor.fetchone()['already_borrowed']:
            return False, "You are already borrowing this item"

        # Check the item is available
        cursor.execute("SELECT type, copies - IFNULL(br.borrowed_count, 0) AS copies_left FROM items t LEFT JOIN (SELECT item, COUNT(*) AS borrowed_count FROM borrows WHERE returned IS NULL GROUP BY item) br ON t.id = br.item WHERE id = ?", (item,))
        copies_left = cursor.fetchone()['copies_left']
        if copies_left <= 0:
            return False, "There are no copies left of this item in Piazza"

        if retrieval_date is None:
            retrieval_date = datetime.now()

        # Check dates are valid
        if planned_return is not None and planned_return < retrieval_date:
            return False, "Planned return date must be after retrieval date"
        if retrieval_date < datetime.now():
            return False, "Retrieval date must be in the future"

        cursor.execute("INSERT INTO borrows (user, item, amount, planned_return, retrieval_date) VALUES (?, ?, ?, ?, ?)",
                       (user, item, 1, planned_return, retrieval_date))

        cursor.execute("SELECT name FROM items WHERE id = ?", (item,))
        item_name = cursor.fetchone()['name']

        self.connection.commit()
        return True, f"Item '{item_name}' borrowed successfully"

    def execute(self, query: str) -> (bool, str):
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            self.connection.commit()
            return True, str(cursor.fetchall())
        except SQLite.Error as e:
            return False, str(e)

    @staticmethod
    def _parseToQuery(filterToken: dict) -> (str, Any):
        value = filterToken['value']
        op = filterToken['operation']
        if filterToken['key'] == "name":
            value = '%' + filterToken['value'] + '%'
            op = "LIKE"
        return f"{filterToken['key']} {op} ?", value

    @staticmethod
    def _parseFilterTokens(filters: str) -> [dict]:
        def splitTokens(candidates: str) -> (str, str, str):
            for operator in ["==", "!=", ">=", "<=", ">", "<"]:  # ">=" and "<=" must be before ">" and "<"
                if operator in candidates:
                    first, third = candidates.split(operator)
                    return first.strip(), operator.strip(), third.strip()
            return "", "", ""

        key_map = {
            "id": ("id", int),
            "name": ("name", str),
            "play": ("play_difficulty", Difficulty),
            "learn": ("learn_difficulty", Difficulty),
            "diff": ("difficulty", Difficulty),
            "min": ("min_players", int),
            "max": ("max_players", int),
            "platform": ("platform", Platform),
            "genre": ("genre", str),
            "pages": ("pages", int),
            "length": ("length", int)
        }

        data = []
        for filterElement in filters.split(","):
            key, operation, value = splitTokens(filterElement)
            key = key.replace(" ", "").replace("_", "").lower()
            converted_value = None
            for k, (mapped_key, value_converter) in key_map.items():
                if not key.startswith(k):
                    continue
                key = mapped_key
                try:
                    converted_value = value_converter[value.upper()].value if issubclass(value_converter, Enum) else value_converter(value)
                except (KeyError, ValueError):
                    pass  # Exception is ignored since converted_value is still None, so we just ignore the filter
                break
            if converted_value is None or (
                    key in ["platform", "genre", "name", "id"] and operation not in ["==", "!="]):
                continue
            data.append({"key": key, "operation": operation, "value": converted_value})
        return data
