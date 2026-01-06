import uuid

import discord
from discord import app_commands
from discord.ext import commands

from core import game as gamemod, piece, move as movemod
from piece import PieceColor
from game import GameState

from data import db as chessdb

# TODO: improve these caches
gameid_to_game = {}
users_to_gameid = {}
cooldowns = {}
players_data = {}

TIMEOUT = 180  # seconds
COOLDOWN = 15


async def validate_user(to_id, ctx) -> bool:
    if to_id != ctx.user.id:
        await ctx.followup.send(
            content="This button is not meant for you, silly", ephemeral=True
        )
        return False
    return True


class BaseView(discord.ui.View):
    def __init__(self, user_id, timeout=TIMEOUT):
        super().__init__(timeout=TIMEOUT)
        self.user_id = user_id

    async def interaction_check(self, interaction) -> bool:
        if self.user_id != interaction.user.id:
            await interaction.response.send_message(
                "This interaction is not for you", ephemeral=True
            )
            return False
        return True

    def disable_all(self):
        for child in self.children:
            child.disabled = True

class DrawView(BaseView):
    def __init__(self, dodraw, user_id):
        super().__init__(user_id)
        self.dodraw = dodraw

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, ctx, button: discord.ui.Button):
        self.disable_all()
        await self.dodraw()
        await ctx.response.edit_message(content="Drew Successfully", view=self)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, ctx, button: discord.ui.Button):
        self.disable_all()
        await ctx.response.edit_message(content="Draw rejected.", view=self)


class GameOptionView(BaseView):
    def __init__(self, user_id, on_accept):
        super().__init__(user_id)
        self.user_id = user_id
        self.on_accept = on_accept

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, ctx, button: discord.ui.Button):
        self.disable_all()
        await self.on_accept()
        await ctx.response.edit_message(content="Game Accepted!", view=self)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, ctx, button: discord.ui.Button):
        self.disable_all()
        await ctx.response.edit_message(content="Game Declined.", view=self)




class ResignButton(BaseView):
    def __init__(self, onresign, user_id):
        super().__init__(user_id)
        self.onresign = onresign

    @discord.ui.button(label="Resign", style=discord.ButtonStyle.danger)
    async def resign(self, ctx, button: discord.ui.Button):
        self.disable_all()
        await self.onresign()
        await ctx.response.edit_message(content="Resigned",view=self)


class GameSession(gamemod.Game):
    def __init__(self, player1: discord.Member, player2: discord.Member, msg=None):
        super().__init__()
        self.id = uuid.uuid4()
        self.player1 = player1
        self.player2 = player2
        self.msg = msg  # the message to edit when updating embed

    def is_turn(self, player: int) -> bool:
        if player != self.player1.id and player != self.player2.id:
            return  # raise an exception maybe idk

        needed = (
            piece.PieceColor.White
            if player == self.player1.id
            else piece.PieceColor.Black
        )
        return needed == self.turn

    def last_move(self) -> None | movemod.Move:
        if self.played_moves:
            return self.played_moves[-1][1]

    def get_embed(self) -> discord.Embed:
        p1 = self.player1
        p2 = self.player2
        title = ""
        match self.state:
            case GameState.Playing:
                title = (
                    f"White ({p1.name})"
                    if self.turn == PieceColor.White
                    else f"Black ({p2.name})"
                ) + " to play"
            case GameState.Draw:
                title = "Draw"
            case GameState.WinWhite:
                title = f"{p1.name} won!"
            case GameState.WinBlack:
                title = f"{p2.name} won!"

        desc = f"<:wking:1456615925057847461> ** {p1.mention} ** | <:bking:1456616121439621368> ** {p2.mention} **\n"

        if len(self.played_moves) > 0:
            DIST_BETWEEN_MOVES = 10
            desc += "```"
            for i, (_full_move, min_move) in enumerate(self.played_moves):
                move_str = str(min_move)
                if i % 2 == 0:
                    desc += str(i // 2 + 1) + ". "
                desc += move_str + " "
                if (i + 1) % 2 == 0:
                    desc += "\n"
                else:
                    desc += " " * (DIST_BETWEEN_MOVES - len(str(move_str)))
            desc += "```"
        color = 0xFFFFFF if self.turn == PieceColor.White else 0
        embed = discord.Embed(title=title, description=desc, color=color)

        return embed

    def get_id(self):
        return self.id

    def to_match_data(self) -> chessdb.MatchData:
        return chessdb.MatchData(
            self.id,
            self.played_moves,
            self.player1.id,
            self.player2.id,
            self.state,
            self.turn,
        )

    @staticmethod
    def from_match_data(
        m: chessdb.MatchData, player1: discord.User, player2: discord.User
    ):
        """
        Returns GameSession object from MatchData object given player1 and player2.
        The reason to pass in the two extra discord.User params is because to retrieve the User objects we need the Bot object. But I don't want to pass the Bot object to this method.
        """
        g = GameSession(player1, player2)
        g.play_san_str(" ".join(m.moves_full))
        g.id = m._id
        g.turn = m.turn
        return g


class Chess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Start a game of chess with someone else")
    @app_commands.describe(against="Player to play against")
    async def start(self, ctx, against: discord.User):
        await ctx.response.defer()

        if not await self._handle_cooldown(ctx):
            return
        await self._try_load_active_game_from_user_id(ctx.user.id)

        if against.id == ctx.user.id:
            await ctx.followup.send('❌ Cant play against yourself silly')
            return 

        if against.bot:
            await ctx.followup.send("❌ Cant play against a bot, silly")
            return

        if ctx.user.id in users_to_gameid:
            await ctx.followup.send(
                "❌ Cannot create a new game when you already have a previous one running."
            )
            return

        if against.id in users_to_gameid:
            await ctx.followup.send(
                "❌ Cannot create a new game when the other person already has a previous game running."
            )
            return

        async def on_accept():
            g = GameSession(ctx.user, against)
            gameid = g.id
            gameid_to_game[gameid] = g

            users_to_gameid[ctx.user.id] = gameid
            users_to_gameid[against.id] = gameid

            g.to_match_data().insert_to_db()

            msg = await self._send_game_with_embed(ctx, g)
            g.msg = msg

        await ctx.followup.send(
            f"{against.mention}, {ctx.user.mention} challenges you to a game of chess. Do you accept?",
            view=GameOptionView(against.id, on_accept),
        )

    @app_commands.command(description="Start a game of chess with someone else")
    @app_commands.describe(move="Player to play against")
    async def play(self, ctx, move: str):
        await ctx.response.defer(ephemeral=True)

        game = await self._try_get_game_of_user(ctx)
        if not game:
            return

        if not game.is_turn(ctx.user.id):
            await ctx.followup.send("❌ Not your move")
            return

        if not game.play_san(move):
            await ctx.followup.send("❌ Invalid move, idiot")
            return

        if game.state != GameState.Playing:
            self._save_and_delete_game(game)

        game.to_match_data().update_on_db()

        await ctx.followup.send(f"✅ Played the move: {str(game.last_move())}")
        await self._show_board(ctx, game)

    @app_commands.command(description="Resign a game of chess, you quitter")
    async def resign(self, ctx):
        await ctx.response.defer()

        if not await self._handle_cooldown(ctx):
            return
        await self._try_load_active_game_from_user_id(ctx.user.id)

        game = await self._try_get_game_of_user(ctx)
        if not game:
            return

        async def onresign():
            game.state = (
                GameState.WinBlack
                if ctx.user.id == game.player1.id
                else GameState.WinWhite
            )
            self._save_and_delete_game(game)
            await self._send_game_with_embed(ctx, game)

        await ctx.followup.send(
            content="Are you sure you want to resign",
            view=ResignButton(onresign, ctx.user.id),
        )

    @app_commands.command(description="Offer a draw on the current game you're playing")
    async def draw(self, ctx):
        await ctx.response.defer(ephemeral=True)

        if not await self._handle_cooldown(ctx):
            return
        await self._try_load_active_game_from_user_id(ctx.user.id)

        game = await self._try_get_game_of_user(ctx)
        if not game:
            return

        other_player = game.player2 if ctx.user.id == game.player1.id else game.player1

        async def ondraw():
            game.state = GameState.Draw
            self._save_and_delete_game(game)
            await self._show_board(ctx, game)

        await ctx.followup.send(
            "Sent a draw, waiting for player to accept", ephemeral=False
        )
        await game.msg.reply(
            content=f"{other_player.mention}, do you accept a draw?",
            view=DrawView(ondraw, other_player.id),
        )

    @app_commands.command(description="Get a user's stats")
    @app_commands.describe(user="User to get data of. Leave blank to get your own data")
    async def profile(self, ctx, user: None | discord.User):
        await ctx.response.defer()
        p = user if user else ctx.user
        p_data = chessdb.PlayerData.from_id(p.id) or chessdb.PlayerData(p.id)
        embed = (
            discord.Embed(title=f"{p.name}'s profile")
            .set_thumbnail(url=p.avatar.url)
            .add_field(
                name="Number of Matches", value=str(p_data.num_matches), inline=True
            )
            .add_field(name="Number of Wins", value=str(p_data.num_wins), inline=True)
            .add_field(name="Number of Draws", value=str(p_data.num_draws), inline=True)
            .add_field(
                name="Number of Losses", value=str(p_data.num_losses), inline=True
            )
        )

        await ctx.followup.send(embed=embed)

    async def _handle_cooldown(self, ctx) -> bool:
        """Handles if user is on cooldown or not, and adds or updates them accordingly"""

        import datetime

        now = datetime.datetime.now().timestamp()
        if ctx.user.id in cooldowns:
            if now - cooldowns[ctx.user.id] < COOLDOWN:
                await ctx.followup.send(content="❌ You're on a cooldown")
                return False

        cooldowns[ctx.user.id] = now
        return True

    async def _show_board(self, ctx, game: GameSession):
        """
        Helper function to check and either edit the previous message, or send a new message to display the board, based on the time difference
        """
        import datetime

        if not game.msg:
            game.msg = await self._send_game_with_embed(ctx, game)
            return

        t = game.msg.edited_at or game.msg.created_at
        if int(datetime.datetime.now().timestamp() - t.timestamp()) > TIMEOUT:
            game.msg = await self._send_game_with_embed(ctx, game)
        else:
            await self._update_game_embed(ctx, game)

    async def _try_get_game_of_user(self, ctx) -> None | GameSession:
        if ctx.user.id not in users_to_gameid:
            await self._try_load_active_game_from_user_id(ctx.user.id)

        gameid = users_to_gameid.get(ctx.user.id)

        if not gameid:
            await ctx.followup.send("❌ You don't have any running games, dumass.!")
            return None

        game = gameid_to_game.get(gameid)

        if not game:
            await ctx.followup.send("❌ Invalid game idk what went wrong")
            return None

        return game

    async def _send_game_with_embed(self, ctx, game: GameSession) -> discord.Message:
        file = self._get_board_as_file(game)
        embed = game.get_embed()
        embed.set_image(url="attachment://board.png")
        return await ctx.followup.send(embed=embed, file=file)

    async def _update_game_embed(self, ctx, game: GameSession):
        file = self._get_board_as_file(game)
        embed = game.get_embed()
        embed.set_image(url="attachment://board.png")
        await game.msg.edit(embed=embed, attachments=[file])

    def _get_board_as_file(
        self, game: GameSession, fname: str = "board.png"
    ) -> discord.File:
        import io

        byte_arr = io.BytesIO()
        img = game.board.to_image()
        img.save(byte_arr, "png")
        byte_arr.seek(0)
        file = discord.File(byte_arr, filename=fname)
        return file

    def _save_and_delete_game(self, game: GameSession):
        """Update database with the game and player data and cleans up the dicts"""
        gameid = game.id
        if gameid not in gameid_to_game:
            return  # consider throwing an error
        gameid_to_game.pop(gameid)

        users_to_gameid.pop(game.player1.id)
        users_to_gameid.pop(game.player2.id)

        local_match_data = game.to_match_data()

        player1_data = chessdb.PlayerData.from_id(
            game.player1.id
        ) or chessdb.PlayerData(game.player1.id)
        player2_data = chessdb.PlayerData.from_id(
            game.player2.id
        ) or chessdb.PlayerData(game.player2.id)

        player1_data.num_matches += 1
        player2_data.num_matches += 1

        # accordingly update their stats
        match game.state:
            case GameState.Playing:
                pass
            case GameState.Draw:
                player1_data.num_draws += 1
                player2_data.num_draws += 1
            case GameState.WinWhite:
                player1_data.num_wins += 1
                player2_data.num_losses += 1
            case GameState.WinBlack:
                player2_data.num_wins += 1
                player1_data.num_losses += 1

        local_match_data.update_on_db()
        player1_data.update_db()
        player2_data.update_db()

    async def _try_load_active_game_from_user_id(self, user_id):
        match_data = chessdb.MatchData.get_active_game_by_userid(user_id)
        if not match_data:
            return

        other_player = (
            match_data.white if user_id == match_data.black else match_data.black
        )
        if other_player in users_to_gameid:
            return  # Maybe throw an error idk

        player1 = await self.bot.fetch_user(match_data.white)
        player2 = await self.bot.fetch_user(match_data.black)

        game = GameSession.from_match_data(match_data, player1, player2)
        gid = game.id
        gameid_to_game[gid] = game

        users_to_gameid[match_data.white] = gid
        users_to_gameid[match_data.black] = gid
