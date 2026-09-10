from enum import Enum
from functools import partial

import discord
from discord import app_commands
from discord.ext import commands
from rapidfuzz import fuzz

from src.database import DBManager
from src.utils.autocomplete import similarItemAutocomplete, similarItems, suggestionAutocomplete
from src.utils.confirm import ConfirmView
from src.utils.paginator import PAGE_SIZE, LazyPaginator, countPages


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


SUGGESTION_TYPE_CHOICES = [app_commands.Choice(name=suggestionType.name.lower(), value=suggestionType.name) for suggestionType in SuggestionType]
SUGGESTION_STATUS_CHOICES = [app_commands.Choice(name=status.name.lower(), value=status.name) for status in SuggestionStatus]


class SuggestionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

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

    @staticmethod
    def getSimilarItems(suggestion: str, limit: int = 3) -> list[str]:
        return [entry['name'] for entry in similarItems(suggestion, limit)]

    @staticmethod
    def notFoundEmbed(suggestion: str) -> discord.Embed:
        names = SuggestionsCog.getAlternatives(suggestion)
        if len(names) > 0:
            string = "Did you mean:"
            for name in names:
                string += f"\n- {name}"
            return discord.Embed(title="Suggestion not found", description=string, color=discord.Color.red())
        return discord.Embed(title="Suggestion not found", description="No similar suggestions found", color=discord.Color.red())

    @staticmethod
    def insertSuggestion(author: int, suggestionName: str, suggestion_type: str) -> discord.Embed:
        success, message = DBManager.getInstance().addSuggestion(author, suggestionName, suggestion_type)
        if not success:
            return discord.Embed(title="Suggestion failed", description=message, color=discord.Color.red())
        return discord.Embed(title="Suggestion added", description=message, color=discord.Color.green())

    @staticmethod
    def voteSuggestion(authorID: int, suggestionName: str, voteCount: int) -> discord.Embed:
        success, errMsg = DBManager.getInstance().voteSuggestion(authorID, suggestionName)
        if not success:
            return discord.Embed(title="Vote failed", description=errMsg, color=discord.Color.red())
        return discord.Embed(title="Suggestion voted", description=f"{suggestionName} now has **{voteCount} votes**", color=discord.Color.green())

    @staticmethod
    def mergeSuggestions(suggestion1: str, suggestion2: str) -> discord.Embed:
        suggestion1Data, suggestion1Votes = DBManager.getInstance().getSuggestion(suggestion1)
        suggestion2Data, suggestion2Votes = DBManager.getInstance().getSuggestion(suggestion2)
        if suggestion1Data is None or suggestion2Data is None:
            return SuggestionsCog.notFoundEmbed(suggestion1 if suggestion1Data is None else suggestion2)
        for vote in suggestion2Votes:
            if vote not in suggestion1Votes:
                DBManager.getInstance().voteSuggestion(vote, suggestion1)
        success, _ = DBManager.getInstance().deleteSuggestion(suggestion2)
        if not success:
            return discord.Embed(title="Merge failed", description="Failed to delete second suggestion", color=discord.Color.red())
        return discord.Embed(title="Merge successful", description="Second suggestion merged into first suggestion", color=discord.Color.green())

    @staticmethod
    def deleteSuggestion(suggestion: str) -> discord.Embed:
        success, _ = DBManager.getInstance().deleteSuggestion(suggestion)
        if not success:
            return SuggestionsCog.notFoundEmbed(suggestion)
        return discord.Embed(title="Deletion successful", description="Suggestion deleted successfully", color=discord.Color.green())

    @app_commands.command(name="suggest", description="Suggest a feature for the bot")
    @app_commands.describe(suggestion="What should be added to Piazza, the autocomplete shows which games are already there",
                           type="Type of the suggestion")
    @app_commands.choices(type=SUGGESTION_TYPE_CHOICES)
    @app_commands.autocomplete(suggestion=similarItemAutocomplete)
    async def suggest(self, interaction: discord.Interaction, suggestion: str, type: str):
        await interaction.response.defer()
        suggestionType = SuggestionType[type.upper()]
        suggestionName = f"[{suggestionType.value}] {suggestion}"
        names = SuggestionsCog.getAlternatives(suggestionName)
        items = SuggestionsCog.getSimilarItems(suggestion) if len(suggestion) > 1 else []
        if len(names) == 0 and len(items) == 0:
            embed = SuggestionsCog.insertSuggestion(interaction.user.id, suggestionName, suggestionType.name)
            await interaction.edit_original_response(embed=embed)
            return
        string = ""
        if len(names) > 0:
            string += "Before you continue, these are the most similar suggestions found:"
            for name in names:
                string += f"\n- **{name}**"
        if len(items) > 0:
            string += ("\n\n" if string != "" else "") + "These games are already in Piazza:"
            for item in items:
                string += f"\n- **{item}**"
        string += "\nIf your suggestion is already here, please cancel and vote on it instead"
        embed = discord.Embed(title="Confirm suggestion", description=string, color=discord.Color.orange())
        view = ConfirmView(interaction.user.id, embed, partial(SuggestionsCog.insertSuggestion, interaction.user.id, suggestionName, suggestionType.name), "Confirm", "Cancel")
        view.message = await interaction.original_response()
        await interaction.edit_original_response(embed=embed, view=view)

    @app_commands.command(name="votesuggestion", description="Vote a suggestion")
    @app_commands.describe(suggestion="Suggestion to vote for")
    @app_commands.autocomplete(suggestion=suggestionAutocomplete)
    async def vote(self, interaction: discord.Interaction, suggestion: str):
        await interaction.response.defer()
        suggestionData, votes = DBManager.getInstance().getSuggestion(suggestion)
        if suggestionData is None:
            names = SuggestionsCog.getAlternatives(suggestion)
            if len(names) > 0:
                string = "Did you mean:"
                for name in names:
                    string += f"\n**- {name}**"
                embed = discord.Embed(title="Suggestion not found", description=string, color=discord.Color.red())
                suggestionData, votes = DBManager.getInstance().getSuggestion(names[0])
                view = ConfirmView(interaction.user.id, embed, partial(SuggestionsCog.voteSuggestion, interaction.user.id, suggestionData['name'], len(votes) + 1), "Vote First Suggestion", "Cancel")
                view.message = await interaction.original_response()
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                embed = discord.Embed(title="Suggestion not found", description="No similar suggestions found", color=discord.Color.red())
                await interaction.edit_original_response(embed=embed)
        else:
            if suggestionData['status'] == SuggestionStatus.BOUGHT.name or suggestionData['status'] == SuggestionStatus.REJECTED.name:
                embed = discord.Embed(title="Vote failed", description="Suggestion is already bought or is rejected", color=discord.Color.red())
                await interaction.edit_original_response(embed=embed)
                return
            embed = SuggestionsCog.voteSuggestion(interaction.user.id, suggestionData['name'], len(votes) + 1)
            await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="getsuggestions", description="Get all suggestions")
    @app_commands.describe(showrejected="Include rejected suggestions", showbought="Include bought suggestions", private="Only show the result to you")
    async def getsuggestions(self, interaction: discord.Interaction, showrejected: bool = False, showbought: bool = False, private: bool = True):
        await interaction.response.defer(ephemeral=private)
        total = DBManager.getInstance().getSuggestionCount(showrejected, showbought)
        if total == 0:
            embed = discord.Embed(title="No suggestions", description="No suggestions have been made yet", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        pages = countPages(total)

        async def loadPage(page: int) -> discord.Embed:
            suggestions = DBManager.getInstance().getSuggestionsPage(showrejected, showbought, PAGE_SIZE, page * PAGE_SIZE)
            items = []
            for index, suggestion in enumerate(suggestions):
                status = SuggestionStatus[suggestion['status']].value
                items.append(f"**{page * PAGE_SIZE + index + 1}.** {status} {suggestion['name']}  **({suggestion['votes']}⭐)**")
            embed = discord.Embed(title="Top Suggestions" if page == 0 else "Suggestions", description="\n".join(items), color=discord.Color.blue())
            embed.set_footer(text=f"page {page + 1} of {pages}")
            return embed

        view = LazyPaginator(pages, loadPage)
        view.message = await interaction.original_response()
        await interaction.edit_original_response(embed=await loadPage(0), view=view)

    @app_commands.command(name="updatesuggestionstatus", description="Update suggestion status")
    @app_commands.describe(suggestion="Suggestion to update", status="New status of the suggestion")
    @app_commands.choices(status=SUGGESTION_STATUS_CHOICES)
    @app_commands.autocomplete(suggestion=suggestionAutocomplete)
    async def updatestatus(self, interaction: discord.Interaction, suggestion: str, status: str):
        await interaction.response.defer()
        success, message = DBManager.getInstance().updateSuggestionStatus(suggestion, SuggestionStatus[status.upper()].name)
        if not success:
            embed = SuggestionsCog.notFoundEmbed(suggestion)
        else:
            embed = discord.Embed(title="Update successful", description=message, color=discord.Color.green())
        await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="mergesuggestion", description="Merge two suggestions into one")
    @app_commands.describe(suggestion1="Suggestion to keep", suggestion2="Suggestion to merge into the first one")
    @app_commands.autocomplete(suggestion1=suggestionAutocomplete, suggestion2=suggestionAutocomplete)
    async def mergesuggestion(self, interaction: discord.Interaction, suggestion1: str, suggestion2: str):
        await interaction.response.defer()
        suggestion1Data, _ = DBManager.getInstance().getSuggestion(suggestion1)
        suggestion2Data, _ = DBManager.getInstance().getSuggestion(suggestion2)
        if suggestion1Data is None or suggestion2Data is None:
            embed = SuggestionsCog.notFoundEmbed(suggestion1 if suggestion1Data is None else suggestion2)
            await interaction.edit_original_response(embed=embed)
            return
        embed = discord.Embed(title="Confirm merge", description=f"Merge **{suggestion2Data['name']}** into **{suggestion1Data['name']}**?\nThe second suggestion will be deleted", color=discord.Color.orange())
        view = ConfirmView(interaction.user.id, embed, partial(SuggestionsCog.mergeSuggestions, suggestion1Data['name'], suggestion2Data['name']), "Merge", "Cancel")
        view.message = await interaction.original_response()
        await interaction.edit_original_response(embed=embed, view=view)

    @app_commands.command(name="deletesuggestion", description="Delete a suggestion")
    @app_commands.describe(suggestion="Suggestion to delete")
    @app_commands.autocomplete(suggestion=suggestionAutocomplete)
    async def deletesuggestion(self, interaction: discord.Interaction, suggestion: str):
        await interaction.response.defer()
        suggestionData, _ = DBManager.getInstance().getSuggestion(suggestion)
        if suggestionData is None:
            embed = SuggestionsCog.notFoundEmbed(suggestion)
            await interaction.edit_original_response(embed=embed)
            return
        embed = discord.Embed(title="Confirm deletion", description=f"Delete the suggestion **{suggestionData['name']}**?", color=discord.Color.orange())
        view = ConfirmView(interaction.user.id, embed, partial(SuggestionsCog.deleteSuggestion, suggestionData['name']), "Delete", "Cancel")
        view.message = await interaction.original_response()
        await interaction.edit_original_response(embed=embed, view=view)
