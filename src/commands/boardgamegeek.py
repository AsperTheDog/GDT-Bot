import requests
import xmltodict

from disnake import ApplicationCommandInteraction, Embed, Color
from disnake.ext.commands import Cog, slash_command

from src.data_models.boardgamemodel import BoardGameModel
from src.utils.paginator import BoardGamePaginator


class BoardGamesCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="bggsearch", description="Fetch boardgame's information from BGG")
    async def fetchBoardgame(self, inter: ApplicationCommandInteraction, name: str):
        await inter.response.send_message("Fetching data from BGG...") # ephemeral=True

        boardgameIds = self.bot.db.getBGGIDFromName(name)

        if len(boardgameIds) == 0:
            embed = Embed(title=f" Boardgame Not Found", description=f"{name} was not found in our database", color=Color.red())
            await inter.edit_original_response(embed=embed)
        else:
            await inter.edit_original_response(f"Fetching data for {name}")

            idsToString = ','.join([f"{id}" for id in boardgameIds])

            url = f'https://boardgamegeek.com/xmlapi2/thing?id={idsToString}&stats=1'

            try:
                response = requests.get(url)
                response.raise_for_status()
                await inter.delete_original_response()

                # xml to dictionary to BoardGameModel class
                game_data = self.__dictParser(xmltodict.parse(response.content))

                await self.__paginate(inter, game_data)

            except requests.exceptions.RequestException as e:
                embed = Embed(title="Query failed", description=f"Error: {e}", color=Color.red())
                await inter.edit_original_response(embed=embed)


    def __dictParser(self, boardGameDict: dict) -> [BoardGameModel]:
        boardGames = []
        def tagsFilter(tagList):
            if tagList["@type"] == "boardgamemechanic":
                return True

        def categoryFilter(categoryList):
            if categoryList["@type"] == "boardgamecategory":
                return True

        items = boardGameDict["items"]
        for item in items["item"]:
            name = item["name"][0]["@value"] if isinstance(item["name"], list) \
                else item["name"]["@value"] if isinstance(item["name"], dict) \
                else ""

            description = item["description"] if len(item["description"]) < 1024 \
                else item["description"][:1020] + "..."

            minPlayers = item["minplayers"]["@value"]
            maxPlayers = item["maxplayers"]["@value"]
            playingTime = item["playingtime"]["@value"]
            categoriesList = list(filter(categoryFilter, item["link"]))[:3]
            gameCategories = ', '.join([categoryItem["@value"] for categoryItem in categoriesList])
            rank = item["statistics"]["ratings"]["ranks"]["rank"][0]["@value"]
            averageRating = item["statistics"]["ratings"]["average"]["@value"]
            bggRating = item["statistics"]["ratings"]["bayesaverage"]["@value"]
            tagsList = list(filter(tagsFilter, item["link"]))[:3]
            tags =', '.join([tag["@value"] for tag in tagsList])
            boardGame = BoardGameModel(
                gameId = item["@id"],
                title= name,
                thumbnail= item["thumbnail"],
                image = item["image"],
                description= description,
                minPlayers= minPlayers,
                maxPlayers= maxPlayers,
                playingTime= playingTime,
                categories= gameCategories,
                rank= rank,
                averageRating= averageRating,
                bggRating= bggRating,
                tags= tags
            )
            boardGames.append(boardGame)
        return boardGames

    async def __paginate(self, inter: ApplicationCommandInteraction, items: [BoardGameModel]):
        embed: Embed = items[0].getEmbed()
        if len(items) == 0:
            embed = Embed(title=f" Parsing Error", description=f"Parsing failed successfully",
                          color=Color.red())
            await inter.edit_original_response(embed=embed)
        elif len(items) == 1:
            await inter.edit_original_response(embed=embed)
        else:
            view = BoardGamePaginator(items, embed)
            embed.set_footer(text="Use arrows to move between pages")
            view.msg = await inter.original_response()
            await view.msg.edit(embed=embed, view=view)