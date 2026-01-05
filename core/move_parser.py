import re
from piece import PieceType
from square import SquarePosition, File
from move import Move, NormalMove, Castling

alpha_to_piece = {
    "P": PieceType.Pawn,  # idk if any engines use this, but FEN deos so why not
    "N": PieceType.Knight,
    "B": PieceType.Bishop,
    "R": PieceType.Rook,
    "Q": PieceType.Queen,
    "K": PieceType.King,
}


class InvalidFileError(Exception):
    def __init__(self, msg):
        self.msg = msg
        super().__init__(msg)


def file_from_alpha(s: str) -> File:
    i = ord(s) - ord("a")
    if 0 < i < ord("a") - ord("h") + 1:
        raise InvalidFileError(s)
    return File(i)


# TODO: improve these regexes
normal_raw = (
    r"\b([RNBQK])?([a-h])?([1-8])?(x?)([a-h])([1-8])(\+)?(\s*e\.p\.)?(=?[RNQB])?[+#]?"
)
normal = re.compile(normal_raw)
all_reg = (
    r"(O-O-O|O-O|(?:[RNBQK]?[a-h]?[1-8]?x?[a-h][1-8](?:\s*e\.p\.)?(?:=?[RNBQ])?)[+#]?)"
)
all_r = re.compile(all_reg)


def parse_move(s: str):
    if s == "O-O":
        return Move(Castling.Short)
    if s == "O-O-O":
        return Move(Castling.Long)

    m = normal.search(s)

    if not m:
        return None
    piece = alpha_to_piece.get(m.group(1)) or PieceType.Pawn
    from_file_s = m.group(2)
    from_rank_s = m.group(3)

    from_ = SquarePosition.empty()

    if from_file_s:
        from_.file = file_from_alpha(from_file_s)
    if from_rank_s:
        from_.rank = int(from_rank_s)

    from_ = None if from_.is_empty() else from_

    is_capture = m.group(4) != ""
    is_en_passant = m.group(8)
    promotion_to = alpha_to_piece[m.group(9)[-1]] if m.group(9) else None

    to_file = file_from_alpha(m.group(5))
    to_rank = int(m.group(6))
    to = SquarePosition(to_file, to_rank)

    nm = NormalMove(
        piece,
        to,
        from_,
        is_capture=is_capture,
        is_en_passant=is_en_passant,
        promotion_to=promotion_to,
    )
    return Move(nm)


def parse_moves(s: str):
    moves = []
    f = all_r.findall(s)
    for m in f:
        v = parse_move(m)
        if not v:
            break
        moves.append(v)

    return moves


def dostuff():
    while True:
        i = input("ENTER YOUR MOVES: ")
        print(parse_moves(i))


if __name__ == "__main__":
    dostuff()
