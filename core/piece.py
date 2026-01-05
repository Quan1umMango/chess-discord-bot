from enum import Enum, IntEnum


class PieceColor(IntEnum):
    White = (0,)
    Black = 1

    def __str__(self):
        return "White" if self == PieceColor.White else "Black"

    def __repr__(self):
        return str(self)

    def compl(self):
        return PieceColor(1 - self)


class PieceType(Enum):
    Null = (0,)
    Pawn = (1,)
    Knight = (3,)
    Rook = (4,)
    Bishop = (5,)
    Queen = (6,)
    King = 7


class Piece:
    def __init__(self, piece_type: PieceType, color: PieceColor):
        self.type = piece_type
        self.color = color

    @staticmethod
    def null():
        return Piece(PieceType.Null, 0)

    @staticmethod
    def pawn(color: PieceColor):
        return Piece(PieceType.Pawn, color)

    @staticmethod
    def knight(color: PieceColor):
        return Piece(PieceType.Knight, color)

    @staticmethod
    def bishop(color: PieceColor):
        return Piece(PieceType.Bishop, color)

    @staticmethod
    def rook(color: PieceColor):
        return Piece(PieceType.Rook, color)

    @staticmethod
    def queen(color: PieceColor):
        return Piece(PieceType.Queen, color)

    @staticmethod
    def king(color: PieceColor):
        return Piece(PieceType.King, color)
