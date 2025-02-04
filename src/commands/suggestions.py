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


class SuggestionStatus(Enum):
    PENDING = "🕐"
    ACCEPTED = "✅"
    REJECTED = "⛔"
    BOUGHT = "💸"


class SuggestionsCog(Cog):
    def __init__(self, bot):
        self.bot: InteractionBot = bot

    @staticmethod
    def getAlternatives(suggestion: str):
        names = DBManager.getInstance().getSuggestionNames()
        similar = []
        for name in names:
            score = fuzz.partial_ratio(name, suggestion)
            similar.append((score, name))
        similar.sort(key=lambda x: x[0], reverse=True)
        names = [s[1] for s in similar][:(3 if len(similar) > 3 else len(similar))]
        return names

    @slash_command(name="suggest", description="Suggest a feature for the bot")
    async def suggest(self, inter: ApplicationCommandInteraction, suggestion: str, type: str):
        def confirmInsertion(author: int, suggestionName: str, suggestion_type: str):
            success, message = DBManager.getInstance().addSuggestion(author, suggestionName, suggestion_type)
            if not success:
                newEmbed: Embed = Embed(title="Suggestion failed", description=message, color=Color.red())
            else:
                newEmbed: Embed = Embed(title="Suggestion added", description=message, color=Color.green())
            return newEmbed

        await inter.response.defer()
        if type.upper() not in ["BOARDGAME", "BOOK", "SWITCH", "PS4", "PS5", "XBOX", "DECK"]:
            embed = Embed(title="Invalid suggestion type", description="Please choose a valid suggestion type.\nValid types are Boardgame, Book, Switch, PS4, PS5, Xbox, Deck", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return

        suggestionType = SuggestionType[type.upper()]
        suggestion = f"[{suggestionType.value}] {suggestion}"
        names = SuggestionsCog.getAlternatives(suggestion)
        if len(names) > 0:
            string = "Before you continue, these are the most similar suggestions found:"
            for name in names:
                string += f"\n**- {name}**"
            string += "\nIf your suggestion is already here, please cancel and vote on it instead"
            embed = Embed(title="Confirm suggestion", description=string, color=Color.orange())
            view = ConfirmDialog(embed, partial(confirmInsertion, inter.author.id, suggestion, suggestionType.name), inter.author.id, "Confirm", "Cancel")
            msg = await inter.original_response()
            await msg.edit(embed=embed, view=view)
        else:
            embed = confirmInsertion(inter.author.id, suggestion, suggestionType.name)
            await inter.edit_original_response(embed=embed)

    @slash_command(name="vote", description="Vote a suggestion")
    async def vote(self, inter: ApplicationCommandInteraction, suggestion: str):
        def confirmVote(authorID: int, suggestionName: str, voteCount: int):
            succ, errMsg = DBManager.getInstance().voteSuggestion(authorID, suggestionName)
            if not succ:
                newEmbed = Embed(title="Vote failed", description=errMsg, color=Color.red())
            else:
                newEmbed = Embed(title="Suggestion voted", description=f"{suggestionName} now has **{voteCount} votes**", color=Color.green())
            return newEmbed

        await inter.response.defer()
        suggestionData, votes = DBManager.getInstance().getSuggestion(suggestion)
        if suggestionData is None:
            names = SuggestionsCog.getAlternatives(suggestion)
            if len(names) > 0:
                string = "Did you mean:"
                for name in names:
                    string += f"\n**- {name}**"
                embed = Embed(title="Suggestion not found", description=string, color=Color.red())
                suggestionData, votes = DBManager.getInstance().getSuggestion(names[0])
                view = ConfirmDialog(embed, partial(confirmVote, inter.author.id, suggestionData['name'], len(votes) + 1), inter.author.id, "Vote First Suggestion", "Cancel")
                msg = await inter.original_response()
                await msg.edit(embed=embed, view=view)
            else:
                embed = Embed(title="Suggestion not found", description="No similar suggestions found", color=Color.red())
                await inter.edit_original_response(embed=embed)
        else:
            embed = confirmVote(authorID=inter.author.id, suggestionName=suggestionData['name'], voteCount=len(votes) + 1)
            await inter.edit_original_response(embed=embed)

    @slash_command(name="getsuggestions", description="Get all suggestions")
    async def getsuggestions(self, inter: ApplicationCommandInteraction):
        await inter.response.defer()
        suggestions = DBManager.getInstance().getSuggestions()
        if len(suggestions) == 0:
            embed = Embed(title="No suggestions", description="No suggestions have been made yet", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        suggestions.sort(key=lambda x: len(x['votes']), reverse=True)
        items = []
        for i, suggestion in enumerate(suggestions):
            status = SuggestionStatus[suggestion['status']].value
            items.append(f"**{i + 1}.** {status} {suggestion['name']}  **({len(suggestion['votes'])}⭐)**")
        view = SuggestionPaginator(items)
        msg = await inter.original_response()
        await msg.edit(view=view, embed=view.embed)

    @slash_command(name="updatestatus", description="Update suggestion status")
    async def updatestatus(self, inter: ApplicationCommandInteraction, suggestion: str, status: str):
        await inter.response.defer()
        status = SuggestionStatus[status.upper()]
        success, message = DBManager.getInstance().updateSuggestionStatus(suggestion, status.name)
        if not success:
            names = SuggestionsCog.getAlternatives(suggestion)
            if len(names) > 0:
                string = "Did you mean:"
                for name in names:
                    string += f"\n- {name}"
                embed = Embed(title="Suggestion not found", description=string, color=Color.red())
            else:
                embed = Embed(title="Suggestion not found", description="No similar suggestions found", color=Color.red())
            await inter.edit_original_response(embed=embed)
        else:
            embed = Embed(title="Update successful", description=message, color=Color.green())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="mergesuggestion", description="Merge two suggestions into one")
    async def mergesuggestion(self, inter: ApplicationCommandInteraction, suggestion1: str, suggestion2: str):
        await inter.response.defer()
        suggestion1Data = DBManager.getInstance().getSuggestion(suggestion1)
        suggestion2Data = DBManager.getInstance().getSuggestion(suggestion2)
        for vote in suggestion2Data['votes']:
            if vote not in suggestion1Data['votes']:
                DBManager.getInstance().voteSuggestion(vote, suggestion1)
        success, _ = DBManager.getInstance().deleteSuggestion(suggestion2)
        if not success:
            embed = Embed(title="Merge failed", description="Failed to delete second suggestion", color=Color.red())
        else:
            embed = Embed(title="Merge successful", description="Second suggestion merged into first suggestion", color=Color.green())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="deletesuggestion", description="Delete a suggestion")
    async def deletesuggestion(self, inter: ApplicationCommandInteraction, suggestion: str):
        await inter.response.defer()
        success, _ = DBManager.getInstance().deleteSuggestion(suggestion)
        if not success:
            names = SuggestionsCog.getAlternatives(suggestion)
            if len(names) > 0:
                string = "Did you mean:"
                for name in names:
                    string += f"\n- {name}"
                embed = Embed(title="Suggestion not found", description=string, color=Color.red())
            else:
                embed = Embed(title="Suggestion not found", description="No similar suggestions found", color=Color.red())
        else:
            embed = Embed(title="Deletion successful", description="Suggestion deleted successfully", color=Color.green())
        await inter.edit_original_response(embed=embed)