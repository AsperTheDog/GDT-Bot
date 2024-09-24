from dataclasses import dataclass

from disnake import Embed, Color


@dataclass
class BookObj:
    id: int
    title: str
    author: str
    pages: int
    copies: int
    copies_available: int
    thumbnail: str = "https://i.imgur.com/OJhoTqu.png"
    description: str = "No description available"
    categories: list[str] = ()

    @staticmethod
    def createFromDB(bookDict: dict):
        return BookObj(
            id=bookDict["id"] if "id" in bookDict else -1,
            title=bookDict["name"],
            author=bookDict["author"],
            pages=bookDict["length"],
            copies=bookDict["copies"],
            copies_available=bookDict["available_copies"] if "available_copies" in bookDict else -1,
            thumbnail=bookDict["thumbnail"] if "thumbnail" in bookDict else "https://i.imgur.com/OJhoTqu.png",
            description=bookDict["description"] if "description" in bookDict else "No description available",
            categories=bookDict["categories"] if "categories" in bookDict else []
        )

    def getEmbed(self, flags: [str]) -> Embed:
        color = Color.dark_green()
        if self.copies_available >= 0:
            if self.copies_available == 0:
                color = Color.red()
            else:
                color = Color.green()
        embed = Embed(title=self.title, color=color)
        embed.set_thumbnail(url=self.thumbnail)

        if "compact" not in flags:
            embed.add_field(name="Description", value=f"{self.description}", inline=False)

            categoriesStr = "\n".join(self.categories)
            if "allCats" not in flags and len(self.categories) > 3:
                categoriesStr = "\n".join(self.categories[:3]) + "..."
            if len(self.categories) > 0:
                embed.add_field(name="Categories", value=f"{categoriesStr}", inline=True)
            else:
                embed.add_field(name="Categories", value=f"None", inline=True)

        embed.add_field(name="Author", value=f"{self.author}", inline=True)
        embed.add_field(name="Pages", value=f"{self.pages}", inline=True)
        return embed

    def getInsertQueries(self, nextID: int) -> [(str, list)]:
        queries = []
        self.id = nextID
        insertBookquery = "INSERT INTO books (id, author) VALUES (?, ?);"
        insertBookValues = [self.id, self.author]
        queries.append((insertBookquery, insertBookValues))
        insertItemQuery = "INSERT INTO items (id, name, length, description, thumbnail, type, copies) VALUES (?, ?, ?, ?, ?, ?, ?);"
        insertItemValues = [self.id, self.title, self.pages, self.description, self.thumbnail, "book", self.copies]
        queries.append((insertItemQuery, insertItemValues))
        for category in self.categories:
            insertCategoryQuery = "INSERT INTO categories (id, category) VALUES (?, ?);"
            insertCategoryValues = [self.id, category]
            queries.append((insertCategoryQuery, insertCategoryValues))
        return queries

    def getDict(self):
        return {
            "id": self.id,
            "name": self.title,
            "author": self.author,
            "length": self.pages,
            "copies": self.copies,
            "available_copies": self.copies_available,
            "thumbnail": self.thumbnail,
            "description": self.description,
            "categories": self.categories
        }