import csv
import sqlite3 as SQLite
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from src.embed_helpers.boardgame import BoardGameObj
from src.embed_helpers.book import BookObj
from src.embed_helpers.common import Difficulty, Platform
from src.embed_helpers.videogame import VideoGameObj
from src.files import DATABASE_PATH, OTHER_DIR, query


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


FILTER_COLUMNS: dict[ObjectType, dict[str, str]] = {
    ObjectType.BOARDGAME: {
        "name": "name",
        "play_difficulty": "play_difficulty",
        "learn_difficulty": "learn_difficulty",
        "min_players": "min_players",
        "max_players": "max_players",
        "length": "length"
    },
    ObjectType.VIDEOGAME: {
        "name": "name",
        "difficulty": "difficulty",
        "platform": "platform",
        "min_players": "min_players",
        "max_players": "max_players",
        "length": "length"
    },
    ObjectType.BOOK: {
        "name": "name",
        "author": "author",
        "length": "length"
    }
}

DEFAULT_THUMBNAIL = "https://i.imgur.com/OJhoTqu.png"
DEFAULT_DESCRIPTION = "No description available"
NUMERIC_COLUMNS = ("length", "copies", "min_players", "max_players", "difficulty", "platform", "play_difficulty", "learn_difficulty")

ITEM_COLUMNS = ("name", "description", "thumbnail", "copies", "length")
TYPE_COLUMNS: dict[ObjectType, tuple[str, ...]] = {
    ObjectType.BOARDGAME: ("min_players", "max_players", "play_difficulty", "learn_difficulty"),
    ObjectType.VIDEOGAME: ("min_players", "max_players", "difficulty", "platform"),
    ObjectType.BOOK: ("author",)
}

SQLite.register_adapter(datetime, lambda value: value.isoformat(sep=" "))
SQLite.register_adapter(date, lambda value: value.isoformat())


def normalizeSeedRow(entry: dict) -> dict:
    for column in NUMERIC_COLUMNS:
        if column in entry and not entry[column].strip().isdigit():
            entry[column] = "0"
    return entry


def withPagination(statement: str, limit: int, offset: int, arguments: list) -> str:
    if limit <= 0:
        return statement
    clause = " LIMIT ? "
    arguments.append(limit)
    if offset > 0:
        clause += " OFFSET ? "
        arguments.append(offset)
    return statement.rstrip().rstrip(";") + clause


def parseDateTime(value: str | None) -> datetime | None:
    if value is None:
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            continue
    return None


def dict_factory(cursor, row):
    data = {}
    for index, column in enumerate(cursor.description):
        name = column[0]
        value = row[index]
        if name in ["play_difficulty", "learn_difficulty", "difficulty"]:
            value = Difficulty(value) if value is not None else Difficulty.UNDEFINED
        if name == "platform":
            value = Platform(value) if value is not None else Platform.UNDEFINED
        if name == "type":
            value = ObjectType(value + "s")
        if name in ["returned", "planned_return", "retrieval_date", "register_date", "declared_date"]:
            value = parseDateTime(value)
        if name == "categories":
            value = value.split(",") if value is not None else []
        data[name] = value
    return data


class DBManager:
    instance: 'DBManager' = None

    def __init__(self, database: str):
        self.path: str = database
        self.closed = False
        self.needsPopulating = not Path(database).exists()
        self._createDatabase()
        print("Database connection established")
        DBManager.instance = self

    def close(self):
        if getattr(self, "closed", True):
            return
        self.closed = True
        print("Closing database connection...")
        self.connection.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _createDatabase(self):
        print("Initializing database...")
        self.connection: SQLite.Connection = SQLite.connect(self.path)
        self.connection.row_factory = dict_factory
        cursor: SQLite.Cursor = self.connection.cursor()
        cursor.executescript(query("generateDB.sql"))
        self.connection.commit()

    async def populateDefaultData(self, bggEnabled: bool = True):
        from src.bgg import BGGUnavailable, fetchBGGameData

        print("Populating default data...")
        cursor: SQLite.Cursor = self.connection.cursor()

        with open(OTHER_DIR / "boardgames.csv", "r", newline="", encoding="utf-8") as data:
            boardgameRows = [normalizeSeedRow(row) for row in csv.DictReader(data)]
        bggRows = {int(row["bgg_id"]): row for row in boardgameRows if row["bgg_id"] != ""}
        games = {}
        if bggEnabled and len(bggRows) > 0:
            try:
                fetched = await fetchBGGameData(list(bggRows.keys()), bggRows, lambda x: print(f"Populating DB: {x} games done"))
            except BGGUnavailable as error:
                print(f"Skipping BoardGameGeek data: {error}")
            else:
                games = {game.bggId: game for game in fetched}
        for row in boardgameRows:
            game = games.get(int(row["bgg_id"]) if row["bgg_id"] != "" else -1) or BoardGameObj.createFromDB(row)
            for statement, values in game.getInsertQueries(self.getNextItemID()):
                cursor.execute(statement, values)

        with open(OTHER_DIR / "videogames.csv", "r", newline="", encoding="utf-8") as data:
            for entry in csv.DictReader(data):
                normalized = normalizeSeedRow(entry)
                for statement, values in VideoGameObj.createFromDB(normalized).getInsertQueries(self.getNextItemID()):
                    cursor.execute(statement, values)

        with open(OTHER_DIR / "books.csv", "r", newline="", encoding="utf-8") as data:
            for entry in csv.DictReader(data):
                normalized = normalizeSeedRow(entry)
                normalized["categories"] = [category.strip() for category in normalized["categories"].split(",") if category.strip() != ""]
                for statement, values in BookObj.createFromDB(normalized).getInsertQueries(self.getNextItemID()):
                    cursor.execute(statement, values)

        self.connection.commit()

    def getItemIDFromName(self, name: str) -> int:
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM items WHERE LOWER(name) = LOWER(?)", (name,))
        data = cursor.fetchone()
        if data is None:
            try:
                itemID = int(name)
            except ValueError:
                return -1
            else:
                cursor.execute("SELECT EXISTS(SELECT 1 FROM items WHERE id = ?) AS item_exists", (itemID,))
                return itemID if cursor.fetchone()['item_exists'] else -1
        return data['id']

    def getItemNameFromID(self, id: int) -> str:
        cursor = self.connection.cursor()
        cursor.execute("SELECT name FROM items WHERE id = ?", (id,))
        data = cursor.fetchone()
        return data['name'] if data is not None else ""

    def getItemAvailableCopies(self, id: int) -> int:
        cursor = self.connection.cursor()
        cursor.execute(query("getItemAvailableCopies.sql"), (id,))
        return cursor.fetchone()['copies_left']

    def searchItems(self, name: str = "", itemType: ObjectType = None, limit: int = 0) -> list[dict]:
        clauses = []
        arguments = []
        if name != "":
            clauses.append("LOWER(name) LIKE LOWER(?)")
            arguments.append("%" + name + "%")
        if itemType is not None:
            clauses.append("type = ?")
            arguments.append(itemType.value[:-1])
        statement = "SELECT id, name FROM items"
        if len(clauses) > 0:
            statement += " WHERE " + " AND ".join(clauses)
        statement += " ORDER BY name ASC"
        if limit > 0:
            statement += " LIMIT ?"
            arguments.append(limit)
        cursor = self.connection.cursor()
        cursor.execute(statement, arguments)
        return cursor.fetchall()

    def getBookAuthors(self, name: str = "", limit: int = 0) -> list[str]:
        arguments = []
        statement = "SELECT DISTINCT author FROM books"
        if name != "":
            statement += " WHERE LOWER(author) LIKE LOWER(?)"
            arguments.append("%" + name + "%")
        statement += " ORDER BY author ASC"
        if limit > 0:
            statement += " LIMIT ?"
            arguments.append(limit)
        cursor = self.connection.cursor()
        cursor.execute(statement, arguments)
        return [row["author"] for row in cursor.fetchall()]

    def getItemsToBorrowFromName(self, user: int, name: str) -> list[dict]:
        cursor = self.connection.cursor()
        statement = query("getItemsToBorrow.sql")
        if name.isdigit():
            cursor.execute(statement.format("i.id = ?"), (int(name), user))
            return cursor.fetchall()
        cursor.execute(statement.format("LOWER(i.name) = LOWER(?)"), (name, user))
        exact = cursor.fetchall()
        if len(exact) > 0:
            return [exact[0]]
        cursor.execute(statement.format("LOWER(i.name) LIKE LOWER('%' || ? || '%')"), (name, user))
        return cursor.fetchall()

    def getItemsToReturnFromName(self, user: int, name: str) -> list[dict]:
        cursor = self.connection.cursor()
        statement = query("getItemsToReturn.sql")
        if name.isdigit():
            cursor.execute(statement.format("i.id = ?"), (int(name), user))
            return cursor.fetchall()
        cursor.execute(statement.format("LOWER(i.name) = LOWER(?)"), (name, user))
        exact = cursor.fetchall()
        if len(exact) > 0:
            return [exact[0]]
        cursor.execute(statement.format("LOWER(i.name) LIKE LOWER('%' || ? || '%')"), (name, user))
        return cursor.fetchall()

    def getUserInterests(self, user: int, name: str = "", limit: int = 0) -> list[dict]:
        arguments = [user]
        statement = "SELECT items.id, items.name FROM interests JOIN items ON interests.item = items.id WHERE interests.user = ?"
        if name != "":
            statement += " AND LOWER(items.name) LIKE LOWER(?)"
            arguments.append("%" + name + "%")
        statement += " ORDER BY items.name ASC"
        if limit > 0:
            statement += " LIMIT ?"
            arguments.append(limit)
        cursor = self.connection.cursor()
        cursor.execute(statement, arguments)
        return cursor.fetchall()

    def getFilteredList(self, itemType: ObjectType, conditions: list[tuple[str, Operation, Any]] = (), ascending: bool = False, limit: int = 0, offset: int = 0) -> list:
        columns = FILTER_COLUMNS[itemType]
        clauses = []
        arguments = [itemType.value[:-1]]
        for key, operation, value in conditions:
            column = columns.get(key)
            if column is None:
                continue
            if column == "name":
                if operation is Operation.Equal:
                    clauses.append("LOWER(name) LIKE LOWER(?)")
                elif operation is Operation.NotEqual:
                    clauses.append("LOWER(name) NOT LIKE LOWER(?)")
                else:
                    continue
                arguments.append("%" + value + "%")
                continue
            clauses.append(f"{column} {operation.value} ?")
            arguments.append(value)
        statement = query("getFilteredList.sql").format(itemType.value)
        if len(clauses) > 0:
            statement += " WHERE " + " AND ".join(clauses)
        if ascending:
            statement += " ORDER BY name ASC "
        if limit > 0:
            statement += " LIMIT ? "
            arguments.append(limit)
            if offset > 0:
                statement += " OFFSET ? "
                arguments.append(offset)
        cursor = self.connection.cursor()
        cursor.execute(statement, arguments)
        items = []
        match itemType:
            case ObjectType.BOARDGAME:
                for entry in cursor.fetchall():
                    items.append(BoardGameObj.createFromDB(entry))
            case ObjectType.VIDEOGAME:
                for entry in cursor.fetchall():
                    items.append(VideoGameObj.createFromDB(entry))
            case ObjectType.BOOK:
                for entry in cursor.fetchall():
                    items.append(BookObj.createFromDB(entry))
        return items

    def getItemData(self, itemType: ObjectType, itemID: int) -> BoardGameObj | VideoGameObj | BookObj | None:
        cursor = self.connection.cursor()
        cursor.execute(query("getItem.sql").format(itemType.value), (itemType.value[:-1], itemID))
        queryResult = cursor.fetchone()
        if queryResult is None:
            return None
        if itemType.value == ObjectType.BOARDGAME.value:
            return BoardGameObj.createFromDB(queryResult)
        if itemType.value == ObjectType.VIDEOGAME.value:
            return VideoGameObj.createFromDB(queryResult)
        return BookObj.createFromDB(queryResult)

    def getBorrowsList(self, user: int = None, item: int = None, current: bool = None, limit: int = 0, offset: int = 0):
        clauses = []
        arguments = []
        if user is not None:
            clauses.append("user = ?")
            arguments.append(user)
        if item is not None:
            clauses.append("item = ?")
            arguments.append(item)
        if current is not None:
            clauses.append("returned IS NULL" if current else "returned IS NOT NULL")
        statement = withPagination(query("getMixedList.sql").format(" WHERE " + " AND ".join(clauses) if len(clauses) > 0 else ""), limit, offset, arguments)
        cursor = self.connection.cursor()
        cursor.execute(statement, arguments)
        return cursor.fetchall()

    def getBorrowsAmount(self, user: int, current: bool) -> int:
        returned = "IS NULL" if current else "IS NOT NULL"
        cursor = self.connection.cursor()
        if user is None:
            cursor.execute(f"SELECT COUNT(*) AS amount FROM borrows WHERE returned {returned}")
        else:
            cursor.execute(f"SELECT COUNT(*) AS amount FROM borrows WHERE user = ? AND returned {returned}", (user,))
        return cursor.fetchone()['amount']

    def getBorrowStats(self, order: str, target: str, limit: int = 0, offset: int = 0) -> [dict]:
        arguments = []
        statement = query("getBorrowStats.sql") if target == "user" else query("getBorrowItemStats.sql")
        statement = withPagination(statement.format(order), limit, offset, arguments)
        cursor = self.connection.cursor()
        cursor.execute(statement, arguments)
        return cursor.fetchall()

    def getBorrowStatsCount(self, target: str) -> int:
        column = "user" if target == "user" else "item"
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT COUNT(DISTINCT {column}) AS total FROM borrows")
        return cursor.fetchone()['total']

    def getReminders(self, now: datetime = None) -> [dict]:
        cursor = self.connection.cursor()
        cursor.execute(query("getReminders.sql"), {"now": (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")})
        return cursor.fetchall()

    def getInterested(self, item: int):
        cursor = self.connection.cursor()
        cursor.execute("SELECT user, declared_date FROM interests WHERE item = ?", (item,))
        return cursor.fetchall()

    def getIDFromBGGID(self, bgg_id: int) -> int:
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM boardgames WHERE bgg_id = ?", (bgg_id,))
        data = cursor.fetchone()
        return data['id'] if data is not None else -1

    def getItemIDByExactName(self, name: str) -> int:
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM items WHERE LOWER(name) = LOWER(?)", (name,))
        data = cursor.fetchone()
        return data['id'] if data is not None else -1

    def getItemType(self, itemID: int) -> ObjectType | None:
        cursor = self.connection.cursor()
        cursor.execute("SELECT type FROM items WHERE id = ?", (itemID,))
        data = cursor.fetchone()
        return None if data is None else data['type']

    def getItemUsage(self, itemID: int) -> dict:
        cursor = self.connection.cursor()
        cursor.execute("SELECT (SELECT COUNT(*) FROM borrows WHERE item = ?) AS borrows, (SELECT COUNT(*) FROM borrows WHERE item = ? AND returned IS NULL) AS borrowed, (SELECT COUNT(*) FROM interests WHERE item = ?) AS interests", (itemID, itemID, itemID))
        return cursor.fetchone()

    def addCopies(self, itemID: int, copies: int) -> int:
        cursor = self.connection.cursor()
        cursor.execute("UPDATE items SET copies = copies + ? WHERE id = ?", (copies, itemID))
        self.connection.commit()
        return itemID

    def deleteItem(self, itemID: int) -> tuple[bool, str]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT name, copies, copies - IFNULL((SELECT COUNT(*) FROM borrows WHERE item = ? AND returned IS NULL), 0) AS available FROM items WHERE id = ?", (itemID, itemID))
        data = cursor.fetchone()
        if data is None:
            return False, "This item does not exist"
        borrowed = data['copies'] - data['available']
        if borrowed > 0:
            return False, f"There are {borrowed} copies currently borrowed, they have to be returned first"
        cursor.execute("DELETE FROM borrows WHERE item = ?", (itemID,))
        cursor.execute("DELETE FROM interests WHERE item = ?", (itemID,))
        cursor.execute("DELETE FROM categories WHERE id = ?", (itemID,))
        for itemType in TYPE_COLUMNS:
            cursor.execute(f"DELETE FROM {itemType.value} WHERE id = ?", (itemID,))
        cursor.execute("DELETE FROM items WHERE id = ?", (itemID,))
        self.connection.commit()
        return True, f"Item '{data['name']}' deleted successfully"

    def getNextItemID(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT MAX(id) AS max_id FROM items")
        elem = cursor.fetchone()['max_id']
        return elem + 1 if elem is not None else 0

    def _insertItem(self, item: BoardGameObj | VideoGameObj | BookObj) -> int | None:
        cursor = self.connection.cursor()
        try:
            for statement, values in item.getInsertQueries(self.getNextItemID()):
                cursor.execute(statement, values)
            self.connection.commit()
        except SQLite.IntegrityError:
            self.connection.rollback()
            return None
        return item.id

    async def insertBoardgameFromBGG(self, bggID: int, play_difficulty: Difficulty, learn_difficulty: Difficulty, copies: int) -> bool:
        from src.bgg import fetchBGGameData

        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM boardgames WHERE bgg_id = ?", (bggID,))
        existingData = cursor.fetchone()
        if existingData is not None:
            cursor.execute("UPDATE items SET copies = copies + ? WHERE id = ?", (copies, existingData['id']))
            self.connection.commit()
            return True

        extraData = {bggID: {
            "play_difficulty": play_difficulty,
            "learn_difficulty": learn_difficulty,
            "copies": copies
        }}
        games = await fetchBGGameData([bggID], extraData)
        if len(games) == 0:
            return False
        return self._insertItem(games[0]) is not None

    def insertBoardgameManual(self, name: str, min_players: int, max_players: int, length: int, description: str, thumbnail: str, categories: list[str], copies: int, bggID: int, play_difficulty: Difficulty, learn_difficulty: Difficulty) -> int | None:
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM items WHERE LOWER(name) = LOWER(?)", (name,))
        existingData = cursor.fetchone()
        if existingData is not None:
            return self.addCopies(existingData['id'], copies)
        return self._insertItem(BoardGameObj(
            id=-1,
            title=name,
            minPlayers=min_players,
            maxPlayers=max_players,
            playingTime=length,
            copies=copies,
            copies_available=copies,
            bggId=bggID,
            description=description if description != "" else DEFAULT_DESCRIPTION,
            thumbnail=thumbnail if thumbnail != "" else DEFAULT_THUMBNAIL,
            categories=categories,
            play_difficulty=play_difficulty,
            learn_difficulty=learn_difficulty
        ))

    def insertVideogame(self, name: str, platform: Platform, difficulty: Difficulty, min_players: int, max_players: int, length: int, copies: int) -> int | None:
        existing = self.getItemIDByExactName(name)
        if existing != -1:
            return self.addCopies(existing, copies)
        return self._insertItem(VideoGameObj.createFromDB({
            "name": name,
            "platform": platform,
            "difficulty": difficulty,
            "min_players": min_players,
            "max_players": max_players,
            "length": length,
            "copies": copies
        }))

    def insertBook(self, name: str, author: str, pages: int, abstract: str, copies: int) -> int | None:
        existing = self.getItemIDByExactName(name)
        if existing != -1:
            return self.addCopies(existing, copies)
        return self._insertItem(BookObj.createFromDB({
            "name": name,
            "author": author,
            "length": pages,
            "description": abstract if abstract != "" else DEFAULT_DESCRIPTION,
            "copies": copies
        }))

    def updateItem(self, itemType: ObjectType, itemID: int, values: dict) -> bool:
        itemValues = {key: value for key, value in values.items() if key in ITEM_COLUMNS}
        typeValues = {key: value for key, value in values.items() if key in TYPE_COLUMNS[itemType]}
        cursor = self.connection.cursor()
        try:
            if len(itemValues) > 0:
                assignments = ", ".join(f"{column} = ?" for column in itemValues)
                cursor.execute(f"UPDATE items SET {assignments} WHERE id = ?", [*itemValues.values(), itemID])
            if len(typeValues) > 0:
                assignments = ", ".join(f"{column} = ?" for column in typeValues)
                cursor.execute(f"UPDATE {itemType.value} SET {assignments} WHERE id = ?", [*typeValues.values(), itemID])
            self.connection.commit()
        except SQLite.IntegrityError:
            self.connection.rollback()
            return False
        return True

    def setCategories(self, itemID: int, categories: list[str]) -> bool:
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM categories WHERE id = ?", (itemID,))
        for category in categories:
            cursor.execute("INSERT INTO categories (id, category) VALUES (?, ?)", (itemID, category))
        self.connection.commit()
        return True

    def borrowItem(self, user: int, item: int, planned_return: datetime, retrieval_date: datetime) -> (bool, str):
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM items WHERE id = ?) AS item_exists", (item,))
        if not cursor.fetchone()['item_exists']:
            return False, "This item does not exist"

        cursor.execute("SELECT EXISTS(SELECT 1 FROM borrows WHERE user = ? AND item = ? AND returned IS NULL) AS already_borrowed", (user, item))
        if cursor.fetchone()['already_borrowed']:
            return False, "You are already borrowing this item"

        if self.getItemAvailableCopies(item) <= 0:
            return False, "There are no copies left of this item in Piazza"

        if retrieval_date is None:
            retrieval_date = datetime.now()

        if planned_return is not None and planned_return < retrieval_date:
            return False, "Planned return date must be after retrieval date"
        if retrieval_date > datetime.now():
            return False, "Retrieval date must not be in the future"

        cursor.execute("INSERT INTO borrows (user, item, amount, planned_return, retrieval_date) VALUES (?, ?, ?, ?, ?)",
                       (user, item, 1, planned_return, retrieval_date))
        item_name = self.getItemNameFromID(item)

        self.connection.commit()
        return True, f"Item '{item_name}' borrowed successfully"

    def returnItem(self, user: int, item: int) -> (bool, str):
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM items WHERE id = ?) AS item_exists", (item,))
        if not cursor.fetchone()['item_exists']:
            return False, "This item does not exist"

        cursor.execute("SELECT EXISTS(SELECT 1 FROM borrows WHERE user = ? AND item = ? AND returned IS NULL) AS already_borrowed", (user, item))
        if not cursor.fetchone()['already_borrowed']:
            return False, "You are not borrwing this item"

        cursor.execute("UPDATE borrows SET returned = ? WHERE user = ? AND item = ? AND returned IS NULL", (datetime.now(), user, item))
        self.connection.commit()

        item_name = self.getItemNameFromID(item)
        return True, f"Item '{item_name}' returned successfully"

    def returnAllItems(self, user: int):
        cursor = self.connection.cursor()
        cursor.execute("SELECT items.name FROM borrows JOIN items ON borrows.item = items.id WHERE user = ? AND returned IS NULL", (user,))
        items = cursor.fetchall()

        if len(items) == 0:
            return False, "You are not borrowing any items"

        cursor.execute("UPDATE borrows SET returned = ? WHERE user = ? AND returned IS NULL", (datetime.now(), user))
        self.connection.commit()
        return True, "Successfully returned the following items:\n- " + "\n- ".join([item['name'] for item in items])

    def setReminderSent(self, user: int, item: int) -> bool:
        cursor = self.connection.cursor()
        cursor.execute("UPDATE borrows SET reminded = TRUE WHERE user = ? and item = ?", (user, item))
        self.connection.commit()
        return True

    def declareInterest(self, user: int, item: str | int):
        if isinstance(item, str):
            item = self.getItemIDFromName(item)
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM interests WHERE user = ? AND item = ?) AS already_interested", (user, item))
        if cursor.fetchone()['already_interested']:
            return False
        cursor.execute("INSERT INTO interests (user, item) VALUES (?, ?)", (user, item))
        self.connection.commit()
        return True

    def cancelInterest(self, user: int, item: str | int):
        if isinstance(item, str):
            item = self.getItemIDFromName(item)
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM interests WHERE user = ? AND item = ?) AS already_interested", (user, item))
        if not cursor.fetchone()['already_interested']:
            return False
        cursor.execute("DELETE FROM interests WHERE user = ? AND item = ?", (user, item))
        self.connection.commit()
        return True

    def addSuggestion(self, user: int, suggestion: str, suggestion_type: str):
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM suggestions WHERE name = ?) AS suggestion_exists", (suggestion,))
        if cursor.fetchone()['suggestion_exists']:
            return False, "This suggestion already exists"
        cursor.execute("INSERT INTO suggestions (name, proposer, suggestion_type) VALUES (?, ?, ?)", (suggestion, user, suggestion_type))
        cursor.execute("INSERT INTO suggestion_votes (user, name) VALUES (?, ?)", (user, suggestion))
        self.connection.commit()
        return True, f"A suggestion for **{suggestion}** was added successfully"

    def deleteSuggestion(self, suggestion: str):
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM suggestions WHERE name = ?) AS suggestion_exists", (suggestion,))
        if not cursor.fetchone()['suggestion_exists']:
            return False, "This suggestion does not exist"
        cursor.execute("DELETE FROM suggestions WHERE name = ?", (suggestion,))
        cursor.execute("DELETE FROM suggestion_votes WHERE name = ?", (suggestion,))
        self.connection.commit()
        return True, "Suggestion deleted successfully"

    def getSuggestionNames(self, suggestion_type: str = "", search: str = "", limit: int = 0) -> list[str]:
        clauses = []
        arguments = []
        if suggestion_type != "":
            clauses.append("suggestion_type = ?")
            arguments.append(suggestion_type)
        if search != "":
            clauses.append("LOWER(name) LIKE LOWER(?)")
            arguments.append("%" + search + "%")
        statement = "SELECT name FROM suggestions"
        if len(clauses) > 0:
            statement += " WHERE " + " AND ".join(clauses)
        statement += " ORDER BY name ASC"
        if limit > 0:
            statement += " LIMIT ?"
            arguments.append(limit)
        cursor = self.connection.cursor()
        cursor.execute(statement, arguments)
        return [suggestion['name'] for suggestion in cursor.fetchall()]

    def getSuggestion(self, suggestion: str):
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM suggestions WHERE name = ?) AS suggestion_exists", (suggestion,))
        if not cursor.fetchone()['suggestion_exists']:
            return None, None
        cursor.execute("SELECT * FROM suggestions WHERE name = ?", (suggestion,))
        data = cursor.fetchone()
        cursor.execute("SELECT user FROM suggestion_votes WHERE name = ?", (suggestion,))
        votes = [vote['user'] for vote in cursor.fetchall()]
        return data, votes

    def getSuggestionsPage(self, showRejected: bool = False, showBought: bool = False, limit: int = 0, offset: int = 0) -> list[dict]:
        arguments = []
        statement = withPagination(query("getSuggestionsPage.sql").format(self._suggestionsFilter(showRejected, showBought)), limit, offset, arguments)
        cursor = self.connection.cursor()
        cursor.execute(statement, arguments)
        return cursor.fetchall()

    def getSuggestionCount(self, showRejected: bool = False, showBought: bool = False) -> int:
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM suggestions" + self._suggestionsFilter(showRejected, showBought))
        return cursor.fetchone()['total']

    @staticmethod
    def _suggestionsFilter(showRejected: bool, showBought: bool) -> str:
        clauses = []
        if not showRejected:
            clauses.append("status != 'REJECTED'")
        if not showBought:
            clauses.append("status != 'BOUGHT'")
        return (" WHERE " + " AND ".join(clauses)) if len(clauses) > 0 else ""

    def voteSuggestion(self, user: int, suggestion: str):
        cursor = self.connection.cursor()
        suggestionData, votes = self.getSuggestion(suggestion)
        if suggestionData is None:
            return False, "This suggestion does not exist"
        if user in votes:
            return False, "You have already voted for this suggestion"
        cursor.execute("INSERT INTO suggestion_votes (user, name) VALUES (?, ?)", (user, suggestion))
        cursor.execute("UPDATE suggestions SET likes = likes + 1 WHERE name = ?", (suggestion,))
        self.connection.commit()
        return True, "Vote registered successfully"

    def updateSuggestionStatus(self, suggestion: str, status: str):
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM suggestions WHERE name = ?) AS suggestion_exists", (suggestion,))
        if not cursor.fetchone()['suggestion_exists']:
            return False, "This suggestion does not exist"
        cursor.execute("UPDATE suggestions SET status = ? WHERE name = ?", (status, suggestion))
        self.connection.commit()
        return True, "Suggestion status updated successfully"

    def execute(self, statement: str) -> (bool, str):
        try:
            cursor = self.connection.cursor()
            cursor.execute(statement)
            self.connection.commit()
            return True, str(cursor.fetchall())
        except SQLite.Error as error:
            return False, str(error)

    @staticmethod
    def getInstance() -> 'DBManager':
        if DBManager.instance is None:
            DBManager(str(DATABASE_PATH))
        return DBManager.instance
