import os
import sqlite3 as SQLite
import csv
from datetime import datetime

from enum import Enum
from typing import Any

from src.embed_helpers.boardgame import BoardGameObj
from src.embed_helpers.book import BookObj
from src.embed_helpers.common import Difficulty, Platform
from src.embed_helpers.videogame import VideoGameObj


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
        if col[0] in ["returned", "planned_return", "retrieval_date", "register_date", "declared_date"]:
            if d[col[0]] is not None:
                try:
                    d[col[0]] = datetime.strptime(d[col[0]], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        d[col[0]] = datetime.strptime(d[col[0]], "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        d[col[0]] = datetime.strptime(d[col[0]], "%Y-%m-%d")
            else:
                d[col[0]] = None
        if col[0] == "categories":
            d[col[0]] = d[col[0]].split(",") if d[col[0]] is not None else []
    return d


class DBManager:
    instance: 'DBManager' = None

    def __init__(self, database: str):
        self.path: str = database
        self._createDatabase(not os.path.exists(database))
        print("Database connection established")

    def __del__(self):
        print("Closing database connection...")
        self.connection.close()

    def _createDatabase(self, hardReset: bool = False):
        print("Initializing database...")
        if hardReset and os.path.exists(self.path):
            os.remove(self.path)
        self.connection: SQLite.Connection = SQLite.connect(self.path)
        self.connection.row_factory = dict_factory
        cursor: SQLite.Cursor = self.connection.cursor()

        with open("data_files/queries/generateDB.sql", 'r') as data:
            cursor.executescript(data.read())

        if hardReset:
            from src.bgg import fetchBGGameData

            print("Populating default data...")
            with open("data_files/other/boardgames.csv", 'r') as data:
                csvData = csv.DictReader(data)
                games = {}
                customGames = []
                for row in csvData:
                    if row['bgg_id'] == "":
                        customGames.append(row)
                    else:
                        games[row['bgg_id']] = row
            for game in fetchBGGameData(list(games.keys()), games, lambda x: print(f"Populating DB: {x} games done")):
                queries = game.getInsertQueries(self.getNextItemID())
                for query, values in queries:
                    cursor.execute(query, values)
            for game in customGames:
                queries = BoardGameObj.createFromDB(game).getInsertQueries(self.getNextItemID())
                for query, values in queries:
                    cursor.execute(query, values)

            with open("data_files/other/videogames.csv", 'r') as data:
                csvData = csv.DictReader(data)
                for entry in csvData:
                    queries = VideoGameObj.createFromDB(entry).getInsertQueries(self.getNextItemID())
                    for query, values in queries:
                        cursor.execute(query, values)

            with open("data_files/other/books.csv", 'r') as data:
                csvData = csv.DictReader(data)
                for entry in csvData:
                    queries = BookObj.createFromDB(entry).getInsertQueries(self.getNextItemID())
                    for query, values in queries:
                        cursor.execute(query, values)

        self.connection.commit()

    def searchIDsFromName(self, name: str) -> [int]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM items WHERE LOWER(name) LIKE LOWER(?)", ("%" + name + "%",))
        data = cursor.fetchall()
        if len(data) == 0:
            try:
                itemID = int(name)
            except ValueError:
                return []
            else:
                cursor.execute("SELECT EXISTS(SELECT 1 FROM items WHERE id = ?) AS item_exists", (itemID,))
                return [itemID] if cursor.fetchone()['item_exists'] else []
        return [item['id'] for item in data]

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
        return data['id'] if data is not None else -1

    def getItemsToBorrowFromName(self, user: int, name: str):
        cursor = self.connection.cursor()
        with open("data_files/queries/getItemsToBorrow.sql", 'r') as data:
            cursor.execute(data.read().format("LOWER(i.name) = LOWER(?)"), (name, user))
            res = cursor.fetchall()
            if len(res) == 0:
                data.seek(0)
                cursor.execute(data.read().format("LOWER(i.name) LIKE LOWER('%' || ? || '%')"), (name, user))
            else:
                return [res[0]['id']]
        return [item['id'] for item in cursor.fetchall()]

    def getItemsToReturnFromName(self, user: int, name: str):
        cursor = self.connection.cursor()
        with open("data_files/queries/getItemsToReturn.sql", 'r') as data:
            cursor.execute(data.read().format("LOWER(i.name) = LOWER(?)"), (name, user))
            res = cursor.fetchall()
            if len(res) == 0:
                data.seek(0)
                cursor.execute(data.read().format("LOWER(i.name) LIKE LOWER('%' || ? || '%')"), (name, user))
            else:
                return [res[0]['id']]
        return [item['id'] for item in cursor.fetchall()]

    def getItemNameFromID(self, id: int) -> str:
        cursor = self.connection.cursor()
        cursor.execute("SELECT name FROM items WHERE id = ?", (id,))
        data = cursor.fetchone()
        return data['name'] if data is not None else ""

    def getItemAvailableCopies(self, id: int) -> int:
        cursor = self.connection.cursor()
        with open("data_files/queries/getItemAvailableCopies.sql", 'r') as data:
            cursor.execute(data.read(), (id,))
        return cursor.fetchone()['copies_left']

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
        with open("data_files/queries/getItem.sql", 'r') as data:
            cursor.execute(data.read().format(itemType.value), (itemType.value[:-1], itemID))
        queryResult = cursor.fetchone()
        if queryResult is None:
            return None
        if itemType.value == ObjectType.BOARDGAME.value:
            return BoardGameObj.createFromDB(queryResult)
        elif itemType.value == ObjectType.VIDEOGAME.value:
            return VideoGameObj.createFromDB(queryResult)
        else:
            return BookObj.createFromDB(queryResult)

    def getBorrowsList(self, user: int = None, item: int = None, current: bool = None):
        cursor = self.connection.cursor()
        with open("data_files/queries/getMixedList.sql", 'r') as data:
            query = data.read()
        finalFilter = ""
        args = []
        if user is not None:
            args.append(user)
        if item is not None:
            args.append(item)
        finalFilter += "WHERE user = ?" if user is not None else ""
        if item is not None:
            finalFilter += ("WHERE" if finalFilter == "" else "AND") + f" item = ?"
        if current is not None:
            finalFilter += ("WHERE" if finalFilter == "" else "AND") + f" returned IS {"" if current else "NOT"} NULL"
        cursor.execute(query.format(finalFilter), args)
        return cursor.fetchall()

    def getBorrowsAmount(self, user: int, current: bool) -> int:
        cursor = self.connection.cursor()
        if user is None:
            cursor.execute(f"SELECT COUNT(*) AS amount FROM borrows WHERE returned IS {"" if current else "NOT"} NULL")
        else:
            cursor.execute(f"SELECT COUNT(*) AS amount FROM borrows WHERE user = ? AND returned IS {"" if current else "NOT"} NULL", (user,))
        return cursor.fetchone()['amount']

    def getBorrowStats(self, order: str, target: str) -> [dict]:
        cursor = self.connection.cursor()
        if target == "user":
            with open("data_files/queries/getBorrowStats.sql", 'r') as data:
                cursor.execute(data.read().format(order))
        else:
            with open("data_files/queries/getBorrowItemStats.sql", 'r') as data:
                cursor.execute(data.read().format(order))
        return cursor.fetchall()

    def getReminders(self) -> [dict]:
        cursor = self.connection.cursor()
        with open("data_files/queries/getReminders.sql", 'r') as data:
            cursor.execute(data.read())
        return cursor.fetchall()

    def getInterested(self, item: int):
        cursor = self.connection.cursor()
        cursor.execute("SELECT user, declared_date FROM interests WHERE item = ?", (item,))
        return cursor.fetchall()

    def returnItem(self, user: int, item: int) -> (bool, str):
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

    def returnAllItems(self, user: int):
        cursor = self.connection.cursor()

        # Get all game names that the user is borrowing
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

    def insertBoardgame(self, bggCode: int, play_difficulty: Difficulty, learn_difficulty: Difficulty, copies: int) -> bool:
        cursor = self.connection.cursor()

        cursor.execute("SELECT id FROM boardgames WHERE bgg_id = ?", (bggCode,))
        existingData = cursor.fetchone()
        if existingData is not None:
            cursor.execute("UPDATE items SET copies = copies + ? WHERE id = ?", (copies, existingData['id']))
            return True

        extraData = {bggCode: {
            "play_difficulty": play_difficulty,
            "learn_difficulty": learn_difficulty,
            "copies": copies
        }}
        from src.bgg import fetchBGGameData
        game = fetchBGGameData([bggCode], extraData)
        if len(game) == 0:
            return False
        queries = game[0].getInsertQueries(self.getNextItemID())
        for query, values in queries:
            cursor.execute(query, values)
        self.connection.commit()
        return True

    def deleteBoardgame(self, itemID: int) -> bool:
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM items WHERE id = ?", (itemID,))
        self.connection.commit()
        return True

    def insertVideogame(self, name: str, platform: Platform, difficulty: Difficulty, min_players: int, max_players: int, length: int, copies: int) -> bool:
        cursor = self.connection.cursor()
        game = VideoGameObj.createFromDB({
            "name": name,
            "platform": platform,
            "difficulty": difficulty,
            "min_players": min_players,
            "max_players": max_players,
            "length": length,
            "copies": copies
        })
        queries = game.getInsertQueries(self.getNextItemID())
        for query, values in queries:
            cursor.execute(query, values)
        self.connection.commit()
        return True

    def deleteVideogame(self, itemID: int) -> bool:
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM items WHERE id = ?", (itemID,))
        self.connection.commit()
        return True

    def insertBook(self, name: str, author: str, pages: int, genre: str, abstract: str, copies: int) -> bool:
        cursor = self.connection.cursor()
        book = BookObj.createFromDB({
            "name": name,
            "author": author,
            "pages": pages,
            "genre": genre,
            "abstract": abstract,
            "copies": copies
        })
        queries = book.getInsertQueries(self.getNextItemID())
        for query, values in queries:
            cursor.execute(query, values)
        self.connection.commit()
        return True

    def deleteBook(self, itemID: int) -> bool:
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM items WHERE id = ?", (itemID,))
        self.connection.commit()
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
        if retrieval_date > datetime.now():
            return False, "Retrieval date must not be in the future"

        cursor.execute("INSERT INTO borrows (user, item, amount, planned_return, retrieval_date) VALUES (?, ?, ?, ?, ?)",
                       (user, item, 1, planned_return, retrieval_date))

        cursor.execute("SELECT name FROM items WHERE id = ?", (item,))
        item_name = cursor.fetchone()['name']

        self.connection.commit()
        return True, f"Item '{item_name}' borrowed successfully"

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

    def getSuggestionNames(self, suggestion_type: str = ""):
        cursor = self.connection.cursor()
        if suggestion_type == "":
            cursor.execute("SELECT name FROM suggestions")
        else:
            cursor.execute("SELECT name FROM suggestions WHERE suggestion_type = ?", (suggestion_type,))
        names = [suggestion['name'] for suggestion in cursor.fetchall()]
        return names

    def getSuggestion(self, suggestion: str):
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM suggestions WHERE name = ?) AS suggestion_exists", (suggestion,));
        if not cursor.fetchone()['suggestion_exists']:
            return None, None
        cursor.execute("SELECT * FROM suggestions WHERE name = ?", (suggestion,))
        data = cursor.fetchone()
        votes = []
        cursor.execute("SELECT user FROM suggestion_votes WHERE name = ?", (suggestion,))
        for vote in cursor.fetchall():
            votes.append(vote['user'])
        return data, votes

    def getSuggestions(self):
        cursor = self.connection.cursor()
        suggestions = []
        for suggestion in cursor.execute("SELECT * FROM suggestions").fetchall():
            suggestion['votes'] = []
            for vote in cursor.execute("SELECT user FROM suggestion_votes WHERE name = ?", (suggestion['name'],)).fetchall():
                suggestion['votes'].append(vote['user'])
            suggestions.append(suggestion)
        return suggestions

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

    def unvoteSuggestion(self, user: int, suggestion: str):
        cursor = self.connection.cursor()
        suggestionData, votes = self.getSuggestion(suggestion)
        if suggestionData is None:
            return False, "This suggestion does not exist"
        if user not in votes:
            return False, "You have not voted for this suggestion"
        cursor.execute("DELETE FROM suggestion_votes WHERE user = ? AND name = ?", (user, suggestion))
        if len(votes) == 1:
            cursor.execute("DELETE FROM suggestions WHERE name = ?", (suggestion,))
            self.connection.commit()
            return True, "Vote removed and suggestion deleted"
        else:
            cursor.execute("UPDATE suggestions SET likes = likes - 1 WHERE name = ?", (suggestion,))
        self.connection.commit()
        return True, "Vote removed successfully"

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
            return f"LOWER({filterToken['key']}) LIKE LOWER(?)", value
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

    def getIDFromBGGID(self, bgg_id: int) -> int:
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM boardgames WHERE bgg_id = ?", (bgg_id,))
        data = cursor.fetchone()
        return data['id'] if data is not None else -1

    def getBBGIDFromID(self, id: int) -> int:
        cursor = self.connection.cursor()
        cursor.execute("SELECT bgg_id FROM boardgames WHERE id = ?", (id,))
        data = cursor.fetchone()
        return data['bgg_id'] if data is not None else -1

    def getBGGIDFromName(self, name: str) -> [int]:
        cursor = self.connection.cursor()
        # remove case sensitivity and return all results that start with 'name' str. BGG can handle up to 20 per request.
        cursor.execute(f"SELECT boardgames.bgg_id FROM items JOIN boardgames ON items.id = boardgames.id WHERE LOWER(items.name) LIKE LOWER(?)", ("%" + name + "%",))
        data = cursor.fetchall()
        ids = [item['bgg_id'] for item in data]
        return ids

    def getNextItemID(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT MAX(id) AS max_id FROM items")
        elem = cursor.fetchone()['max_id']
        return elem + 1 if elem is not None else 0

    @staticmethod
    def initInstance(databasePath):
        DBManager.instance = DBManager(databasePath)

    @staticmethod
    def getInstance() -> 'DBManager':
        if DBManager.instance is None:
            DBManager.initInstance("data_files/database.sqlite")
        return DBManager.instance
