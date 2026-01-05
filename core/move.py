from typing import Union, Optional
from enum import Enum
from piece import PieceType, PieceColor
from square import SquarePosition


piece_to_alpha = {
    # PieceType.Pawn: 'P', idk if i should add this
    PieceType.Knight: "N",
    PieceType.Bishop: "B",
    PieceType.Rook: "R",
    PieceType.Queen: "Q",
    PieceType.King: "K",
}


class Castling(Enum):
    Short = (0,)
    Long = 1

    def copy(self):  # lol
        return self


class NormalMove:
    def __init__(
        self,
        piece_type: PieceType,
        to: SquarePosition,
        from_: Optional[SquarePosition] = None,
        is_capture: bool = False,
        is_en_passant: bool = False,
        promotion_to: PieceType = None,
    ):
        self.piece_type = piece_type
        self.to = to
        self.from_ = from_
        self.is_capture = is_capture
        self.is_en_passant = is_en_passant
        self.promotion_to = promotion_to

    def copy(self):
        return NormalMove(
            self.piece_type,
            self.to,
            self.from_,
            self.is_capture,
            self.is_en_passant,
            self.promotion_to,
        )


class Move:
    def __init__(self, move: Union[Castling, NormalMove]):
        self.turn = PieceColor.White
        self.move = move

    def copy(self):
        m = Move(self.move.copy())
        m.turn = self.turn
        return m

    @staticmethod
    def castle():
        return Move(Castling.Short)

    @staticmethod
    def lcastle():
        return Move(Castling.Long)

    def is_normal_move(self):
        return isinstance(self.move, NormalMove)

    def is_castling(self):
        return isinstance(self.move, Castling)

    def __repr__(self):
        if self.is_normal_move():
            suff = ""
            if self.move.piece_type != PieceType.Pawn:
                suff = piece_to_alpha[self.move.piece_type]
            rep = f"{suff}"
            if self.move.from_:
                rep += str(self.move.from_)
            rep += str(self.move.to)
        elif self.move == Castling.Short:
            rep = "O-O"
        elif self.move == Castling.Long:
            rep = "O-O-O"

        return rep
