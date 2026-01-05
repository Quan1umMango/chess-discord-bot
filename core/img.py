from PIL import Image
from piece import PieceType

IMG_SIZE = 64 * 8

SQUARE_SIZE = IMG_SIZE // 8


BLACK = (10, 50, 50, 255)
WHITE = (255, 255, 255, 255)
MOVE_COLOR = (212, 183, 70, 100)

WHITE_PIECES = Image.open("./assets/WhitePieces_Wood.png")
WHITE_PIECES.convert("RGBA")
BLACK_PIECES = Image.open("./assets/BlackPieces_Wood.png")
BLACK_PIECES.convert("RGBA")
PIECE_IMAGES = {}

for i, p_name in enumerate(
    [
        PieceType.Pawn,
        PieceType.Knight,
        PieceType.Rook,
        PieceType.Bishop,
        PieceType.King,
        PieceType.Queen,
    ]
):
    if p_name == PieceType.Null:
        continue
    start = (i) * 16
    end = (i + 1) * 16
    white = WHITE_PIECES.crop((start, 0, end, 16))
    black = BLACK_PIECES.crop((start, 0, end, 16))
    PIECE_IMAGES[p_name] = {"black": black, "white": white}
