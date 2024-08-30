import os
import sqlite3 as SQLite
import csv

from enum import Enum
from typing import Any

from disnake import Embed, Color


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

        cursor.execute("""CREATE TABLE IF NOT EXISTS boardgames (
                        id INTEGER NOT NULL PRIMARY KEY, 
                        name VARCHAR NOT NULL,
                        play_difficulty INTEGER,
                        learn_difficulty INTEGER,
                        min_players INTEGER,
                        max_players INTEGER,
                        copies INTEGER DEFAULT 1,
                        length INTEGER
                    )""")

        cursor.execute("""CREATE TABLE IF NOT EXISTS videogames (
                        id INTEGER NOT NULL PRIMARY KEY, 
                        name VARCHAR NOT NULL,
                        difficulty INTEGER,
                        platform INTEGER,
                        min_players INTEGER,
                        max_players INTEGER,
                        copies INTEGER DEFAULT 1,
                        length INTEGER
                    )""")

        cursor.execute("""CREATE TABLE IF NOT EXISTS books (
                        id INTEGER NOT NULL PRIMARY KEY, 
                        name VARCHAR NOT NULL,
                        author VARCHAR,
                        pages INTEGER,
                        genre VARCHAR,
                        abstract VARCHAR,
                        copies INTEGER DEFAULT 1
                    )""")

        cursor.execute("""CREATE TABLE IF NOT EXISTS borrows (
                        user INTEGER NOT NULL,
                        item INTEGER NOT NULL,
                        type VARCHAR NOT NULL,
                        amount INTEGER NOT NULL,
                        borrow_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        register_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        indented_return DATETIME,
                        returned DATETIME,
                        PRIMARY KEY(user, item, type)
                    )""")

        cursor.execute("""CREATE TABLE IF NOT EXISTS suggestions (
                        name VARCHAR NOT NULL PRIMARY KEY,
                        type VARCHAR NOT NULL,
                        likes INTEGER DEFAULT 1,
                        message INTEGER NOT NULL
                    )""")

        if hardReset:
            print("Populating default data...")
            for file, table in {"data_files/boardgames.csv": "boardgames",
                                "data_files/videogames.csv": "videogames"}.items():
                with open(file, 'r') as data:
                    dr = csv.DictReader(data)
                    for entry in dr:
                        cursor.execute(
                            f"INSERT INTO {table} ({', '.join(entry.keys())}) VALUES ({', '.join(['?' for _ in entry.keys()])})",
                            list(entry.values()))

        connection.commit()
        return connection

    def getFilteredList(self, table: str, orFilters: str, andFilters: str, ascending: bool = False, limit: int = 0, offset: int = 0) -> [dict]:
        orFilterData = self._parseFilterTokens(orFilters)
        andFilterData = self._parseFilterTokens(andFilters)
        query = f"SELECT id FROM {table}"
        cursor = self.connection.cursor()
        queries = []
        arguments = []
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
        print(query)
        print(arguments)
        cursor.execute(query, arguments)
        res = cursor.fetchall()
        return res

    def getItemEmbed(self, itemType: ObjectType, itemID: int, extended: bool) -> Embed | None:
        def getBoardgameEmbed(data: dict) -> Embed:
            color: Color = Color.dark_green() if data['copies_left'] > 0 else Color.red()
            embed = Embed(title=data['name'], color=color)
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
            embed = Embed(title=data['name'], color=color)
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
            embed = Embed(title=data['name'], color=color)
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
        cursor.execute(f"""SELECT *, t.copies - IFNULL(br.borrowed_count, 0) AS copies_left FROM {itemType.value} t
                            LEFT JOIN (
                                SELECT item, COUNT(*) AS borrowed_count
                                FROM borrows
                                WHERE type = ? AND returned IS NULL
                                GROUP BY item
                            ) br ON t.id = br.item WHERE id = ?""", (itemType.value[:-1], itemID))
        queryResult = cursor.fetchone()
        if queryResult is None:
            return None
        if itemType.value == ObjectType.BOARDGAME.value:
            return getBoardgameEmbed(queryResult)
        elif itemType.value == ObjectType.VIDEOGAME.value:
            return getVideogameEmbed(queryResult)
        else:
            return getBookEmbed(queryResult)

    def getListEmbed(self, itemType: ObjectType, items: [int], range: (int, int)) -> Embed:
        def getBoardgameField() -> str:
            return ""

        def getVideogameField() -> str:
            return ""

        def getBookField() -> str:
            return ""

        cursor = self.connection.cursor()
        cursor.executemany(f"""SELECT *, (t.copies - IFNULL(br.borrowed_count, 0)) > 0 AS available FROM {itemType.value} t
                                LEFT JOIN (
                                SELECT item, COUNT(*) AS borrowed_count
                                FROM borrows
                                WHERE type = ? AND returned IS NULL
                                GROUP BY item
                            ) br ON t.id = br.item WHERE id = ?""", [(itemType.value[:-1], itemID) for itemID in items[range[0]:range[1]]])
        data = cursor.fetchall()

    # TODO: Make method take data from BGG
    def insertBoardgame(self, bggCode: int, name: str, play_difficulty: Difficulty, learn_difficulty: Difficulty, min_players: int, max_players: int, length: int, copies: int) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute("INSERT INTO boardgames (id, name, play_difficulty, learn_difficulty, min_players, max_players, length, copies) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (bggCode, name, play_difficulty.value, learn_difficulty.value, min_players, max_players, length, copies))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

    def deleteBoardgame(self, bggCode: int) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute("DELETE FROM boardgames WHERE id = ?", (bggCode,))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

    def insertVideogame(self, name: str, platform: Platform, difficulty: Difficulty, min_players: int, max_players: int, length: int, copies: int) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute("INSERT INTO videogames (name, platform, difficulty, min_players, max_players, length, copies) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (name, platform.value, difficulty.value, min_players, max_players, length, copies))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

    def deleteVideogame(self, name: str) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute("DELETE FROM videogames WHERE name = ?", (name,))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

    def editCopies(self, itemType: ObjectType, itemID: int, copies: int) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute(f"UPDATE {itemType.value} SET copies = ? WHERE id = ?", (copies, itemID))
            self.connection.commit()
        except SQLite.IntegrityError:
            return False
        return True

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
                    converted_value = value_converter[value.upper()].value if issubclass(value_converter,
                                                                                         Enum) else value_converter(
                        value)
                except (KeyError, ValueError):
                    pass  # Exception is ignored since converted_value is still None, so we just ignore the filter
                break
            if converted_value is None or (
                    key in ["platform", "genre", "name", "id"] and operation not in ["==", "!="]):
                continue
            data.append({"key": key, "operation": operation, "value": converted_value})
        return data
