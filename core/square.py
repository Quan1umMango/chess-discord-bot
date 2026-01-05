from enum import IntEnum
from piece import PieceColor


class InvalidSquareInitError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg


class File(IntEnum):
    A = (0,)
    B = (1,)
    C = (2,)
    D = (3,)
    E = (4,)
    F = (5,)
    G = (6,)
    H = 7

    def __str__(self):
        match self:
            case File.A:
                return "a"
            case File.B:
                return "b"
            case File.C:
                return "c"
            case File.D:
                return "d"
            case File.E:
                return "e"
            case File.F:
                return "f"
            case File.G:
                return "g"
            case File.H:
                return "h"


class SquarePosition:
    def __init__(self, file: File, rank: int):
        if rank < 1 or rank > 8:
            raise InvalidSquareInitError(str(rank))
        if type(file) is int:
            file = File(file)
        self.file = file
        self.rank = rank

    @staticmethod
    def empty():
        s = SquarePosition(File.A, 1)
        s.file = None
        s.rank = None
        return s

    def to_index(self) -> int:
        return (self.rank - 1) * 8 + self.file

    def is_empty(self) -> bool:
        return self.file is None and self.rank is None

    def is_partial(self) -> bool:
        """
        A partial sqaure position is one where only the rank or the file is known. The other unfilled part is for the engine to figure out.
        """
        return not self.is_empty() and (not self.rank or not self.file)

    def get_sq_color(self) -> PieceColor:
        rank_starting_color = (
            PieceColor.White if self.rank % 2 == 0 else PieceColor.Black
        )
        return PieceColor(
            (rank_starting_color + (self.file % 2)) % 2
        )  # trust me this works

    @staticmethod
    def from_index(i):
        file = File(i % 8)
        rank = i // 8 + 1
        return SquarePosition(file, rank)

    def __str__(self):
        return f"{str(self.file)}{self.rank}"

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other):
        if isinstance(other, SquarePosition):
            return self.file == other.file and self.rank == other.rank
        return False
