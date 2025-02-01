from enum import Enum
from functools import partial

from disnake import ApplicationCommandInteraction, Embed, Color
from disnake.ext.commands import Cog, InteractionBot, slash_command

from src.database import DBManager

from fuzzywuzzy import fuzz

from src.utils.confirm import ConfirmDialog
from src.utils.suggestion_paginator import SuggestionPaginator


class SuggestionType(Enum):
    BOARDGAME = "BOARD"
    BOOK = "BOOK"
    SWITCH = "SWITCH"
    PS4 = "PS4"
    PS5 = "PS5"
    XBOX = "XBOX"
    DECK = "DECK"


class SuggestionsCog(Cog):
    def __init__(self, bot):
        self.bot: InteractionBot = bot

    @slash_command(name="suggest", description="Suggest a feature for the bot")
    async def suggest(self, inter: ApplicationCommandInteraction, suggestion: str, type: str):
        def confirmInsertion(author: int, suggestionName: str, suggestionType: str):
            success, message = DBManager.getInstance().addSuggestion(author, suggestionName, suggestionType)
            if not success:
                newEmbed: Embed = Embed(title="Suggestion failed", description=message, color=Color.red())
            else:
                newEmbed: Embed = Embed(title="Suggestion added", description=message, color=Color.green())
            return newEmbed
        await inter.response.defer()
        if suggestion.upper() not in ["BOARDGAME", "BOOK", "SWITCH", "PS4", "PS5", "XBOX", "DECK"]:
            embed = Embed(title="Invalid suggestion type", description="Please choose a valid suggestion type.\nValid types are Boardgame, Book, Switch, PS4, PS5, Xbox, Deck", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return

        suggestionType = SuggestionType[type.upper()]
        suggestion = f"[{suggestionType.value}] {suggestion}"
        names = DBManager.getInstance().getSuggestionNames(suggestionType.name)
        similar = []
        for name in names:
            if fuzz.partial_ratio(name, suggestion) > 75:
                similar.append(name)
        if len(similar) > 0:
            string = "The following similar suggestions have been found:"
            for s in similar:
                string += f"\n**- {s}**"
            string += "\nIf your suggestion is already here, please cancel and vote on it instead"
            embed = Embed(title="Similar suggestions found", description=string, color=Color.orange())
            view = ConfirmDialog(embed, partial(confirmInsertion, inter.author.id, suggestion, suggestionType.name), "Insert", "Cancel")
            msg = await inter.original_response()
            await msg.edit(embed=embed, view=view)
        else:
            embed = confirmInsertion(inter.author.id, suggestion, suggestionType.name)
            await inter.edit_original_response(embed=embed)

    @slash_command(name="vote", description="Vote a suggestion")
    async def vote(self, inter: ApplicationCommandInteraction, suggestion: str):
        await inter.response.defer()
        suggestionData, votes = DBManager.getInstance().getSuggestion(suggestion)
        if suggestionData is None:
            names = DBManager.getInstance().getSuggestionNames()
            similar = []
            for name in names:
                score = fuzz.partial_ratio(name, suggestion)
                similar.append((score, name))
            similar.sort(key=lambda x: x[0], reverse=True)
            names = [s[1] for s in similar][:(3 if len(similar) > 3 else len(similar))]
            string = "Did you mean:"
            for name in names:
                string += f"\n- {name}"
            embed = Embed(title="Suggestion not found", description=string, color=Color.red())
        else:
            success, message = DBManager.getInstance().voteSuggestion(inter.author.id, suggestionData['name'])
            if not success:
                embed = Embed(title="Vote failed", description=message, color=Color.red())
            else:
                embed = Embed(title="Suggestion voted", description=f"{suggestionData['name']} now has **{len(votes) + 1} votes**", color=Color.green())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="getsuggestions", description="Get all suggestions")
    async def getsuggestions(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        suggestions = DBManager.getInstance().getSuggestions()
        if len(suggestions) == 0:
            embed = Embed(title="No suggestions", description="No suggestions have been made yet", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        suggestions.sort(key=lambda x: x['votes'], reverse=True)
        items = []
        for i, suggestion in enumerate(suggestions):
            items.append(f"**{i + 1}.** {suggestion['name']}  **({len(suggestion['votes'])}⭐)**")
        view = SuggestionPaginator(items)
        msg = await inter.original_response()
        await msg.edit(view=view, embed=view.embed)
