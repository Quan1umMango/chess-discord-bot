import move_parser
import board
from piece import PieceColor, Piece, PieceType
from img import SQUARE_SIZE, IMG_SIZE
from square import SquarePosition, File
from move import Castling

from typing import Optional
from enum import IntEnum


class InvalidFEN(Exception):
    pass


class GameState(IntEnum):
    Playing = (0,)
    Draw = (1,)
    WinWhite = (2,)
    WinBlack = 3


class Game:
    def __init__(
        self,
        config: Optional[Optional[Piece]] = None,
        turn: PieceColor = PieceColor.White,
    ):
        if config:
            assert len(config) == 8 * 8, (
                f"Incomplete configuration was given. Excepted list with 64 items, got {len(config)}"
            )

        self.board = board.Board()
        if config:
            self.board.config = config

        # Stores a tuple of (the played move with all the details,the minimum info required to make the move). Both of these are of the type Move
        # the first item of the tuple will be used to easily quickly make the moves, if someone wants to undo or redo a move. The second part of the tuple is to store the raw move given
        self.played_moves = []

        self.starting_turn = turn  # This is stored to determine who played which move, even though you can figure it out using the current turn, this is more clearer
        self.turn = turn
        self.state = self.eval_state()

    @staticmethod
    def from_FEN(fen: str):
        import re

        # TODO: half move clock and full move counter (if needed)

        reg = r"(?P<config>[1-8rnbqkpRNBQKP/]+) (?P<turn>[wb]) (?P<castlerights>-|[kqKQ]{4}) (?P<enpassant>-|[a-h][36]) (?P<halfmoveclock>\d+) (?P<fullmovecounter>\d+)"

        s = re.match(reg, fen)
        if not s:
            raise InvalidFEN("Unable to match regex.")

        b = board.Board()
        b.config = [None for _ in range(8 * 8)]
        i = len(b.config)

        for c in s.group("config"):
            if c.isdigit():
                i -= int(c)
                continue
            if c == "/":
                if i % 8 != 0:
                    raise InvalidFEN()
                continue
            p = move_parser.alpha_to_piece.get(c.upper())
            if not p:
                raise InvalidFEN(f"No piece associated with letter: {c}")

            color = PieceColor.White if c.isupper() else PieceColor.Black

            # little transposition action to make the pieces properly positioned
            pos = SquarePosition.from_index(i - 1)
            pos.file = File.H - pos.file

            b.config[pos.to_index()] = Piece(p, color)
            i -= 1

        turn = PieceColor.White if s.group("turn") == "w" else PieceColor.Black

        b.can_castle = {
            PieceColor.White: {
                Castling.Long: False,
                Castling.Short: False,
            },
            PieceColor.Black: {
                Castling.Long: False,
                Castling.Short: False,
            },
        }

        for right in s.group("castlerights"):
            if right == "-":
                break
            p = PieceColor.White if right.isupper() else PieceColor.Black
            side = Castling.Short if right.lower() == "k" else Castling.Long
            b.can_castle[p][side] = True

        g = Game()
        g.board = b
        g.turn = turn

        return g

    def play_san(self, move_str: str) -> bool:
        """
        Given a string, it checks if it is a valid SAN move, and then plays that move.
        RETURNS: True if the move was played, False otherwise
        """
        move = move_parser.parse_move(move_str)
        if not move:
            return False

        move.turn = self.turn
        played_move = self.board.move_piece(move)
        if not played_move:
            return False

        self.played_moves.append((played_move, move))
        self.turn = PieceColor(1 - self.turn)
        self.state = self.eval_state()
        return True

    def play_san_str(self, moves_str: str):
        """
        Given a string of potentially valid SAN moves, it plays until the end of input has been reached or theres an invalid move that's made.
        RETURNS: True if all the moves were played successfully, False otherwise
        """
        moves = move_parser.parse_moves(moves_str)
        for move in moves:
            move.turn = self.turn
            played_move = self.board.move_piece(move)
            if not played_move:
                return False

            self.played_moves.append((played_move, move))
            self.turn = PieceColor(1 - self.turn)
            self.state = self.eval_state()

        return True

    def eval_state(self) -> GameState:
        turn_is_checkmate = self.board.is_checkmate(self.turn)
        comp_turn_is_checkmate = self.board.is_checkmate(self.turn.compl())

        is_draw = self.is_draw()

        if turn_is_checkmate:
            return (
                GameState.WinWhite
                if self.turn == PieceColor.White
                else GameState.WinBlack
            )
        if comp_turn_is_checkmate:
            return (
                GameState.WinWhite
                if self.turn == PieceColor.Black
                else GameState.WinWhite
            )

        if is_draw:
            return GameState.Draw

        return GameState.Playing

    def is_threefold_rep(self) -> bool:
        """Checks for threefold repetitions"""
        if len(self.played_moves) < 8:
            return False
        if len(set([str(x[0]) for x in self.played_moves[-8:-1]])) == 4:
            return True
        return False

    def is_fivefold_rep(self) -> bool:
        """Checks for fivefold repetitions"""
        if len(self.played_moves) < 12:
            return False
        s = set([str(x[0]) for x in self.played_moves[-12:-1]])
        if len(s) == 4:
            return True
        print(s, self.played_moves[-12:-1])
        return False

    def fifty_move_rule(self) -> bool:
        """Returns True if a draw can be made based on the fifty move rule"""
        if len(self.played_moves) < 50 * 2:
            return False
        for m, _ in self.played_moves[-1:-101]:
            if m.is_normal() and (
                m.move.piece_type == PieceType.Pawn or m.move.is_capture
            ):
                return False
        return True

    def seventy_five_move_rule(self) -> bool:
        """Returns True if a draw can be made based on the seventy five move rule"""
        if len(self.played_moves) < 75 * 2:
            return False
        for m, _ in self.played_moves[-1 : -(75 * 2 + 1)]:
            if m.is_normal() and (
                m.move.piece_type == PieceType.Pawn or m.move.is_capture
            ):
                return False
        return True

    def impossible_checkmate(self) -> bool:
        """
        Returns True if a checkamte is immpossible with the given configuration.
        The configurations include:
            - Only 2 Kings
            - 2 Kings and a Bishop
            - 2 Kings and a Knight
            - King and Bishop and King and Bishop, where the Bishops are of the same square color
        """
        pieces: [(Piece, int)] = []
        for i, sq in enumerate(self.board.config):
            if not sq:
                continue

            # if theres any other piece besides king, bishop or knight, then its a gaurentee its not a draw yet
            if sq.type in [PieceType.Pawn, PieceType.Rook, PieceType.Queen]:
                return False

            pieces.append((sq, i))

        # The conditions won't be satisfied if there are more than 3 pieces, so automatically its not a draw yet
        if len(pieces) > 3:
            return False

        if len(pieces) == 2:
            # if only kings are there on the board
            if pieces[0][0].type == pieces[1][0].type == PieceType.King:
                return True
            else:
                return False

        if len(pieces) == 3:
            num_kings = 0
            num_bishops = 0
            bishop_poses = []
            num_knights = 0
            for p, pos in pieces:
                if p.type == PieceType.King:
                    num_kings += 1
                elif p.type == PieceType.Bishop:
                    num_bishops += 1
                    bishop_poses.append(pos)
                elif p.type == PieceType.Knight:
                    num_knights += 1

            if num_kings != 2:
                return True  # lol, maybe throw an error in the future

            # if there is only a bishop with two kings, or only a knight with two kings, or just two kings
            if (
                num_bishops <= 1 or num_knights <= 1
            ) and num_bishops + num_knights <= 1:
                return True

            # Two bishops in the same colored sqaures
            if (
                num_bishops == 2
                and SquarePosition.from_index(bishop_poses[0]).get_sq_color()
                == SquarePosition.from_index(bishop_poses[1]).get_sq_color()
            ):
                return True

        return False

    def is_draw(self) -> bool:
        """Returns True ONLY IF the draw is forced. So this excludes threefold repetitions and the fifty move rule, which can be optionally claimed by the players"""
        if (
            self.board.is_stalemate(self.turn)
            or self.board.is_stalemate(self.turn.compl())
            or self.is_fivefold_rep()
            or self.seventy_five_move_rule()
            or self.impossible_checkmate()
        ):
            return True


def dostuff():
    # g = Game.from_FEN("4k3/8/8/8/8/8/8/R3K3 w - - 1 1")
    g = Game()
    g.board.to_image((IMG_SIZE, IMG_SIZE), (SQUARE_SIZE, SQUARE_SIZE)).show()
    while True:
        # b.print_board()
        moves_str = input(f"Enter your move ({str(g.turn)} to move): ")
        if g.play_san_str(moves_str):
            g.board.to_image((IMG_SIZE, IMG_SIZE), (SQUARE_SIZE, SQUARE_SIZE)).show()

        if g.state != GameState.Playing:
            print("g.state: ", g.state)
            break


if __name__ == "__main__":
    dostuff()
