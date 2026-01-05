from square import SquarePosition, File
from move import Move, NormalMove, Castling
from piece import PieceColor, PieceType, Piece
from img import IMG_SIZE, SQUARE_SIZE, PIECE_IMAGES, WHITE, BLACK

from PIL import Image


class InvalidFEN(Exception):
    def __init__(self, msg: str = "Invalid FEN given"):
        super().__init__(msg)
        self.msg = msg

    def __str__(self):
        return self.msg


"""
    Includes the directions of the pieces which they can move EXECEPT THE PAWN. 
    Because the pawn is a very special case, since the direction it moves depends on the its color (either up or down the board), its position (either if its in the initial position, in which case it can also move two steps, or not, in which case only one), if its at the A or H file (in which case it cant capture in a certian direction).
    To generate pawn dirs, use get_pawn_dirs function while specifying the necessary details, which are the parameters of the function
"""
_dirs = {
    PieceType.King: [
        (0, 1),
        (1, 0),
        (1, 1),
        (-1, 0),
        (0, -1),
        (-1, 1),
        (-1, -1),
        (1, -1),
    ],
    PieceType.Rook: [(0, 1), (1, 0), (-1, 0), (0, -1)],
    PieceType.Bishop: [(-1, -1), (-1, 1), (1, -1), (1, 1)],
    PieceType.Queen: [
        (-1, -1),
        (-1, 1),
        (1, -1),
        (1, 1),
        (0, 1),
        (1, 0),
        (-1, 0),
        (0, -1),
    ],
    PieceType.Knight: [
        (-1, 2),
        (-1, -2),
        (1, 2),
        (1, -2),
        (-2, 1),
        (-2, -1),
        (2, 1),
        (2, -1),
    ],
}


def get_pawn_dirs(
    color: PieceColor,
    pos: SquarePosition,
    include_non_captures: bool = True,
    include_captures: bool = True,
):
    forward = 1 if color == PieceColor.White else -1
    res = []

    if include_non_captures:
        if pos.rank != (8 if color == PieceColor.White else 1):
            res.append((0, forward))
        if pos.rank == (2 if color == PieceColor.White else 7):
            res.append((0, 2 * forward))

    if not include_captures:
        return res
    if pos.file != File.A:
        res.append((-1, forward))
    if pos.file != File.H:
        res.append((1, forward))
    return res


def sign(x: int) -> int:
    return (abs(x) // x) if x != 0 else 0


class Board:
    def __init__(self):
        # Our board configuration. 63 represents H8, 0 represents A1
        self.config = [None for f in range(0, 8) for r in range(0, 8)]

        # Represents if the player can castle, assuming the path for the king and rook is clear
        # Esentially, this tracks if the king or the rooks have moved at all
        self.can_castle = {
            PieceColor.White: {
                Castling.Long: True,
                Castling.Short: True,
            },
            PieceColor.Black: {
                Castling.Long: True,
                Castling.Short: True,
            },
        }

        # Represents which file is enpassantable. This means, if a bit is turned on, the pawn on that bit can be enpassant-ed and captured
        # Left most bit represents A file. Right most bit represents H file
        self.en_passant = {
            PieceColor.White: 0b00000000,
            PieceColor.Black: 0b00000000,
        }
        # pawns
        for i in range(8, 16):
            self.config[i] = Piece.pawn(PieceColor.White)
        for i in range(48, 56):
            self.config[i] = Piece.pawn(PieceColor.Black)

        # rooks
        self.config[0] = Piece.rook(PieceColor.White)
        self.config[7] = Piece.rook(PieceColor.White)
        self.config[-8] = Piece.rook(PieceColor.Black)
        self.config[-1] = Piece.rook(PieceColor.Black)

        # knights
        self.config[1] = Piece.knight(PieceColor.White)
        self.config[6] = Piece.knight(PieceColor.White)
        self.config[-7] = Piece.knight(PieceColor.Black)
        self.config[-2] = Piece.knight(PieceColor.Black)

        # bishop
        self.config[2] = Piece.bishop(PieceColor.White)
        self.config[5] = Piece.bishop(PieceColor.White)
        self.config[-6] = Piece.bishop(PieceColor.Black)
        self.config[-3] = Piece.bishop(PieceColor.Black)

        # queen
        self.config[3] = Piece.queen(PieceColor.White)
        self.config[-5] = Piece.queen(PieceColor.Black)

        # king
        self.config[4] = Piece.king(PieceColor.White)
        self.config[-4] = Piece.king(PieceColor.Black)

    def to_image(
        self,
        img_dims: tuple[int, int] = (IMG_SIZE, IMG_SIZE),
        sq_dims: tuple[int, int] = (SQUARE_SIZE, SQUARE_SIZE),
        squares_to_color: dict[SquarePosition, tuple[int, int, int, int]] = None,
    ):
        if squares_to_color is None:
            squares_to_color = {}
        img = Image.new("RGBA", img_dims, (0, 0, 0, 255))
        for k, sq in enumerate(self.config):
            i = k // 8
            j = k % 8
            flippy = (i + j) % 2 == 0  # determines square color lol
            flipped_i = 7 - i
            pos = (j * sq_dims[0], flipped_i * sq_dims[1])
            sq_color = squares_to_color.get(SquarePosition.from_index(k)) or (
                BLACK if flippy else WHITE
            )
            sq_img = Image.new("RGBA", sq_dims, sq_color)
            if sq is not None:
                p_img = PIECE_IMAGES[sq.type][
                    "white" if sq.color == PieceColor.White else "black"
                ]
                p_img.convert("RGBA")
                p_img = p_img.resize(sq_dims)
                sq_img.paste(p_img, (0, 0), p_img)
            img.paste(sq_img, pos)

        return img

    def _move_raw(self, from_: SquarePosition, to: SquarePosition):
        from_i = from_.to_index()
        to_i = to.to_index()
        p = self.config[from_i]
        self.config[from_i] = None
        self.config[to_i] = p

    def move_piece(self, move: Move) -> None | Move:
        inner = None
        m = move.copy()  # copy because we'll be modifying the inner and returning the move which is fully equipped with all the info
        if m.is_normal_move():
            inner = self.move_normal(m.move, m.turn)
        if m.is_castling():
            inner = self.castle(m.move, m.turn)
        if not inner:
            return None
        return Move(inner)

    def move_normal(self, move: NormalMove, turn: PieceColor) -> None | NormalMove:
        from_ = move.from_
        to = move.to
        is_capture = move.is_capture
        avail = []
        file = to.file

        match move.piece_type:
            case PieceType.Pawn:
                avail = self._get_pawn_which_can_move_to(
                    turn, to, from_, is_capture=is_capture
                )
            case PieceType.Rook:
                avail = self._get_rook_which_can_move_to(
                    turn, to, from_, is_capture=is_capture
                )
            case PieceType.Bishop:
                avail = self._get_bishop_which_can_move_to(
                    turn, to, from_, is_capture=is_capture
                )
            case PieceType.Queen:
                avail_as_bish = self._get_bishop_which_can_move_to(
                    turn, to, from_, ptype=PieceType.Queen, is_capture=is_capture
                )
                avail_as_rook = self._get_rook_which_can_move_to(
                    turn, to, from_, ptype=PieceType.Queen, is_capture=is_capture
                )
                avail = avail_as_bish + avail_as_rook

            case PieceType.King:
                if not from_:
                    for i, v in enumerate(self.config):
                        # ASSUMPTION: there is only 1 king of each color on the board
                        if v and v.type == PieceType.King and v.color == turn:
                            from_ = SquarePosition.from_index(i)
                            break
                    if not from_:
                        self.print_board()
                        self.to_image(
                            (IMG_SIZE, IMG_SIZE), (SQUARE_SIZE, SQUARE_SIZE)
                        ).show()

                fi = from_.to_index()
                toi = to.to_index()
                possible_sqs = [
                    fi - 8 - 1,
                    fi - 8,
                    fi - 8 + 1,
                    fi - 1,
                    fi + 1,
                    fi + 8 - 1,
                    fi + 8,
                    fi + 8 + 1,
                ]
                if toi in possible_sqs and (
                    not self.config[toi]
                    or self.config[toi].color != turn
                    and is_capture
                ):
                    avail.append(from_)
            case PieceType.Knight:
                avail = self._get_knight_which_can_move_to(
                    turn, to, from_, is_capture=is_capture
                )

        if len(avail) > 1:  # Ambigous move
            return False

        if len(avail) == 0:
            return None

        ps = avail.pop()

        saved_state = self.copy()

        # Checking valid promotion moves
        if move.piece_type == PieceType.Pawn and to.rank == (
            8 if turn == PieceColor.White else 1
        ):
            if not move.promotion_to:
                return False  # No piece was to promote to was give, therefore its not a valid move
            self.config[ps.to_index()] = Piece(move.promotion_to, turn)

        # Castling updating
        if move.piece_type == PieceType.King:
            self.can_castle[turn] = {Castling.Short: False, Castling.Long: False}
        elif move.piece_type == PieceType.Rook:
            if ps.file == File.A:
                self.can_castle[turn][Castling.Long] = False
            elif ps.file == File.A:
                self.can_castle[turn][Castling.Short] = False

        if self.is_en_passant(turn, to, ps):
            pawn_to_take = SquarePosition(
                to.file, to.rank + (-1 if turn == PieceColor.White else 1)
            )
            self.config[pawn_to_take.to_index()] = None

        # Enpassant updating
        if (
            move.piece_type == PieceType.Pawn
            and abs(ps.to_index() - to.to_index()) == 8 * 2
        ):
            file = int(ps.file)
            self.en_passant[turn] = 1 << file
            self.en_passant[1 - turn] = 0
        else:
            self.en_passant[turn] = 0
            self.en_passant[1 - turn] = 0

        self._move_raw(ps, to)

        if self.is_check(turn):
            self.config = saved_state.config
            self.en_passant = saved_state.en_passant
            self.can_castle = saved_state.can_castle

            return None

        move.from_ = ps
        return move

    def castle(self, move: Castling, turn: PieceColor) -> None | Castling:
        if not self.can_castle[turn][move] or self.is_check(turn):
            return False
        rank = 1 if turn == PieceColor.White else 8

        match move:
            case Castling.Short:
                kpos = SquarePosition(File.E, rank)
                rpos = SquarePosition(File.H, rank)
                move_dir = 1
                sq_visited_by_king = {
                    SquarePosition(File.F, rank),
                    SquarePosition(File.G, rank),
                }
                newkpos = SquarePosition(File.G, rank)
                newrpos = SquarePosition(File.F, rank)

            case Castling.Long:
                kpos = SquarePosition(File.E, rank)
                rpos = SquarePosition(File.A, rank)
                move_dir = -1
                sq_visited_by_king = {
                    SquarePosition(File.D, rank),
                    SquarePosition(File.C, rank),
                }
                newkpos = SquarePosition(File.C, rank)
                newrpos = SquarePosition(File.D, rank)

        king = self.get(kpos)
        rook = self.get(rpos)

        # sanity checks
        if (
            not king
            or king.color != turn
            or not rook
            or rook.color != turn
            or king.type != PieceType.King
            or rook.type != PieceType.Rook
        ):
            return False  # may consider throwing an error here idk

        # check if there is any checks in the files
        if self.get_all_covered_squares(1 - turn, True) & sq_visited_by_king:
            return None

        # check if its clear
        for v in range(1, 3):
            p = SquarePosition(File(move_dir * v + kpos.file), kpos.rank)
            if self.get(p):
                return move

        self._move_raw(kpos, newkpos)
        self._move_raw(rpos, newrpos)

        self.can_castle[turn][move] = False
        self.can_castle[turn][not move] = False

        return move

    def get_covered_squares(
        self, turn: PieceColor, pos: SquarePosition, pawn_captures_only: bool = False
    ):
        """
        Gets all the squares covered by a piece at a position in the board. This includes squares which are occupied by pieces (friendly and non friendly)
        """
        covered = set()
        p = self.get(pos)
        if not p:
            return set()

        dirs = _dirs.get(p.type) or get_pawn_dirs(
            turn, pos, not pawn_captures_only, pawn_captures_only
        )

        # special case for king and pawn and the knight
        if (
            p.type == PieceType.King
            or p.type == PieceType.Pawn
            or p.type == PieceType.Knight
        ):
            for dir_ in dirs:
                i = pos
                try:
                    i = SquarePosition(i.file + dir_[0], i.rank + dir_[1])
                except Exception:
                    continue
                covered.add(i)
            return covered

        for dir_ in dirs:
            i = pos
            while True:
                try:
                    i = SquarePosition(i.file + dir_[0], i.rank + dir_[1])
                except Exception as _:
                    break

                covered.add(i)
                if self.get(i) and self.get(i).color != turn:
                    break
        return covered

    def get_raw_playable_moves(
        self, color: PieceColor, pos: SquarePosition, ptype: PieceType
    ):
        """
        Gets the all playable squares on the for the piece of the given color and position and type. In other words, given a color, position and type of piece, it returns the squares in which the piece can move to.
        Note: This means that it excludes invalid captures (like a piece capturing its another piece of the same color) and potential captures. If you want all the covered squares, then use get_covered_squares which returns all the sqaures covered by the piece of a given color, position and type.
        Note: This also doesn't check for any checks that might happen when a piece is moved to a square.
        """
        playable = set()
        p = self.get(pos)
        if not p:
            return set()

        forward = 1 if p.color == PieceColor.White else -1

        dirs = _dirs.get(p.type) or get_pawn_dirs(color, pos, True, True)

        # special case for king and pawn and the knight
        if (
            p.type == PieceType.King
            or p.type == PieceType.Pawn
            or p.type == PieceType.Knight
        ):
            for dir_ in dirs:
                i = pos
                try:
                    i = SquarePosition(i.file + dir_[0], i.rank + dir_[1])
                except Exception:
                    continue
                if self.get(i) and self.get(i).color == color:
                    continue
                if p.type == PieceType.Pawn:
                    if abs(dir_[1]) == 2 and self.get(
                        SquarePosition(i.file, i.rank - forward)
                    ):
                        continue

                    if dir_[0] == 0 and self.get(i):
                        continue
                    if dir_[0] != 0 and (not self.get(i) or self.get(i).color == color):
                        continue

                playable.add(i)
            return playable

        for dir_ in dirs:
            i = pos
            # god i should really make an iterator for this
            while True:
                try:
                    i = SquarePosition(i.file + dir_[0], i.rank + dir_[1])
                except Exception as _:
                    break

                if self.get(i) and self.get(i).color == color:
                    break
                playable.add(i)
                if self.get(i) and self.get(i).color != color:
                    break
        return playable

    def get_all_covered_squares(self, color: PieceColor, pawn_captures_only: bool):
        """
        Gets all the squares which are covered by the pieces of the given color. This includes squares of potential captures (that is, squares which already contian a piece of the same color, but is protected by another piece of the same color).
        """
        s = set()
        for i, p in enumerate(self.config):
            if p is None or p.color != color:
                continue
            s |= self.get_covered_squares(
                color,
                SquarePosition.from_index(i),
                pawn_captures_only=pawn_captures_only,
            )

        return s

    def is_check(self, turn: PieceColor) -> bool:
        """
        Checks if the king of the given color is in check
        """
        s = self.get_all_covered_squares(1 - turn, True)
        our_king = None
        for i, v in enumerate(self.config):
            if v is None or v.color != turn or v.type != PieceType.King:
                continue
            our_king = SquarePosition.from_index(i)
        return our_king in s

    def has_valid_moves(self, turn: PieceColor) -> bool:
        saved_state = self.copy()
        for i, v in enumerate(self.config):
            if not v or v.color != turn:
                continue
            from_ = SquarePosition.from_index(i)
            playable_moves = self.get_raw_playable_moves(turn, from_, v.type)
            for to in playable_moves:
                self._move_raw(from_, to)
                in_check = self.is_check(turn)

                self.config = saved_state.config.copy()
                self.en_passant = saved_state.en_passant.copy()
                self.can_castle = saved_state.can_castle.copy()

                if in_check:
                    continue
                return True
        return False

    def is_checkmate(self, turn: PieceColor) -> bool:
        return self.is_check(turn) and not self.has_valid_moves(turn)

    def is_stalemate(self, turn: PieceColor) -> bool:
        return not self.is_check(turn) and not self.has_valid_moves(turn)

    def print_board(self):
        for i, sq in enumerate(self.config):
            if i % 8 == 0:
                print()
            pos = SquarePosition.from_index(i)
            print(f"{sq.type if sq else str(pos.file)[-1] + str(pos.rank)}", end=" ")
        print()

    def is_proper_piece(
        self, turn: PieceColor, ptype: PieceType, pos: SquarePosition
    ) -> bool:
        p = self.get(pos)
        return p is not None and p.color == turn and p.type == ptype

    def is_en_passant(self, turn, to, from_):
        if not to.rank == (6 if turn == PieceColor.White else 3):
            return False
        cap_pos = SquarePosition(
            to.file, to.rank + (-1 if turn == PieceColor.White else 1)
        )

        return (
            from_.file is not None
            and self.get(to) is None
            and abs(from_.file - to.file) == 1
            and 1 << to.file == self.en_passant[1 - turn]
            and self.is_proper_piece(1 - turn, PieceType.Pawn, cap_pos)
        )

    def get(self, pos: SquarePosition):
        return self.config[pos.to_index()]

    def _get_pawn_which_can_move_to(
        self,
        turn,
        to: SquarePosition,
        from_: None | SquarePosition = None,
        ptype: PieceType = PieceType.Pawn,
        is_capture: bool = False,
    ):
        avail = []
        if self.get(to) is not None and not (is_capture):
            return []
        if turn == PieceColor.White:
            start = to.to_index()
            end = SquarePosition(to.file, 1).to_index()
            inc = -8
            init_sq = SquarePosition(to.file, 2)
        else:
            start = to.to_index()
            end = SquarePosition(to.file, 8).to_index()
            inc = 8
            init_sq = SquarePosition(to.file, 7)

        if is_capture:
            if not from_:
                return []
            if self.is_en_passant(turn, to, from_):
                from_.rank = 5 if turn == PieceColor.White else 4
                avail.append(from_)
                return avail

            # these conditions dont apply to en passant
            if not (self.get(to) and self.get(to).color != turn):
                return []

            if from_.is_partial():
                if not from_.file:
                    return []  # invalid notation (i think??)
                if abs(from_.file - to.file) != 1:
                    return []  # attempting to capture at file which isnt adjacent
                try:
                    p = SquarePosition(File(from_.file), to.rank + sign(inc))
                except Exception as _e:
                    return []
                piece = self.get(p)
                if piece and piece.type == ptype and piece.color == turn:
                    avail.append(p)
                return avail
            else:
                if abs(from_.rank - to.rank) != 1 or abs(from_.file - to.file) != 1:
                    return []
                avail.append(from_)
                return avail

        for i in range(start, end + 1, inc):
            p1 = SquarePosition.from_index(i)
            p = self.get(p1)
            if not p or p.color != turn or p.type != PieceType.Pawn:
                continue
            dist = abs(p1.rank - to.rank)
            if not (dist == 1 or dist == 2 and p1.rank == init_sq.rank):
                continue
            avail.append(p1)
            break  # break because theres no way any other pawn can also go to the same rank if theyre on the same file
        return avail

    def _get_knight_which_can_move_to(
        self,
        turn,
        to: SquarePosition,
        from_: None | SquarePosition = None,
        ptype: PieceType = PieceType.Knight,
        is_capture: bool = False,
    ):
        # TODO: Add parital move functionality
        avail = []

        possible_dists = [
            (-1, 2),
            (-1, -2),
            (1, 2),
            (1, -2),
            (-2, 1),
            (-2, -1),
            (2, 1),
            (2, -1),
        ]

        def is_valid_start_pos(pos):
            dist = (pos.file - to.file, pos.rank - to.rank)
            return dist in possible_dists

        if self.get(to) and (not is_capture or not self.get(to).color != turn):
            return []
        if (
            from_
            and self.is_proper_piece(turn, PieceType.Knight, from_)
            and is_valid_start_pos(from_)
        ):
            avail.append(from_)

        for dist in possible_dists:
            try:
                p1 = SquarePosition(File(to.file + dist[0]), to.rank + dist[1])
            except Exception as _:
                continue

            if not self.is_proper_piece(turn, PieceType.Knight, p1):
                continue
            avail.append(p1)
        return avail

    def _get_rook_which_can_move_to(
        self,
        turn,
        to: SquarePosition,
        from_: None | SquarePosition = None,
        ptype: PieceType = PieceType.Rook,
        is_capture: bool = False,
    ):
        avail = []

        def is_clear(start_pos):
            spi = start_pos.to_index()
            epi = to.to_index()
            s = min(spi, epi)
            e = max(spi, epi)
            if start_pos.rank == to.rank:
                # we need to check horizontally
                inc = 1
            else:
                # else check veritcally
                inc = 8
            for i in range(s, e, inc):
                if self.config[i] and (not is_capture or self.config[i].color == turn):
                    return False
            return True

        if not from_:
            # left to right, right to left, top to bottom ,bottom to top
            for dir_ in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                if dir_[1] == 0:
                    if dir_[0] > 0:
                        inc = 1
                        start, end = (
                            SquarePosition(File.A, to.rank).to_index(),
                            to.to_index() + 1,
                        )
                    else:
                        inc = -1
                        start, end = (
                            SquarePosition(File.H, to.rank).to_index(),
                            to.to_index() - 1,
                        )
                else:
                    if dir_[1] > 0:
                        inc = -8
                        start, end = (
                            SquarePosition(to.file, 8).to_index(),
                            to.to_index() - 8,
                        )
                    else:
                        inc = 8
                        start, end = (
                            SquarePosition(to.file, 1).to_index(),
                            to.to_index() + 8,
                        )

                for i in range(start, end - inc, inc):
                    piece_to_move = SquarePosition.from_index(i)
                    if not self.is_proper_piece(turn, ptype, piece_to_move):
                        continue

                    pos_to_check_from = SquarePosition.from_index(i + inc)
                    if is_clear(pos_to_check_from):
                        avail.append(piece_to_move)

        elif from_.is_partial():
            # TODO: make this more pleasing to look at
            if not from_.rank:  # if hint given is a file
                if from_.file == to.file:
                    for r in range(1, 9):
                        piece_pos = SquarePosition(from_.file, r)
                        pos_to_check_from = SquarePosition(
                            from_.file, to.rank + sign(to.rank - r)
                        )
                        if self.is_proper_piece(turn, ptype, piece_pos) and is_clear(
                            pos_to_check_from
                        ):
                            avail.append(piece_pos)
                else:
                    piece_pos = SquarePosition(from_.file, to.rank)
                    pos_to_check_from = SquarePosition(
                        from_.file + sign(to.file - from_.file), to.rank
                    )
                    if self.is_proper_piece(turn, ptype, piece_pos) and is_clear(
                        pos_to_check_from
                    ):
                        avail.append(piece_pos)
            else:  # if hint is rank
                if from_.rank == to.rank:
                    for f in range(File.A, File.H + 1):
                        piece_pos = SquarePosition(f, from_.rank)
                        pos_to_check_from = SquarePosition(
                            f + sign(to.file - f), to.rank
                        )
                        if self.is_proper_piece(turn, ptype, piece_pos) and is_clear(
                            pos_to_check_from
                        ):
                            avail.append(piece_pos)
                else:
                    piece_pos = SquarePosition(to.file, from_.rank)
                    pos_to_check_from = SquarePosition(
                        f, from_.rank + sign(to.rank - from_.rank)
                    )
                    if self.is_proper_piece(turn, ptype, piece_pos) and is_clear(
                        pos_to_check_from
                    ):
                        avail.append(piece_pos)
        else:
            if from_.file == to.file:
                if from_.rank > to.rank:
                    inc = -8
                else:
                    inc = 8
            else:
                if from_.file > to.file:
                    inc = 1
                else:
                    inc = -1
            p = self.get(from_)
            pos_to_check_from = SquarePosition.from_index(from_.to_index() + inc)
            if self.is_proper_piece(turn, ptype, p) and is_clear(pos_to_check_from):
                avail.append(from_)
        return avail

    def _get_bishop_which_can_move_to(
        self,
        turn,
        to: SquarePosition,
        from_: None | SquarePosition = None,
        ptype: PieceType = PieceType.Bishop,
        is_capture: bool = False,
    ):
        avail = set()
        dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

        def is_valid_start_pos(start_pos):
            dir_ = (sign(start_pos.file - to.file), sign(start_pos.rank - to.rank))
            num_iters = min(
                abs(start_pos.file - to.file), abs(start_pos.rank - to.rank)
            )
            if num_iters == 0:
                return False
            p = SquarePosition(File(start_pos.file - dir_[0]), start_pos.rank - dir_[1])
            for _ in range(num_iters):
                if p.file == to.file and p.rank == to.rank:
                    return True
                if self.get(p) and (not is_capture or self.get(p).color == turn):
                    return False
                p = SquarePosition(File(p.file - dir_[0]), p.rank - dir_[1])
            return False

        if not from_:
            for dir_ in dirs:
                p = to
                end_file = File.H if dir_[0] > 0 else File.A
                end_rank = 1 if dir_[1] < 0 else 8
                num_iters = min(abs(end_file - p.file), abs(end_rank - p.rank))
                for _ in range(num_iters):
                    try:
                        p = SquarePosition(File(p.file + dir_[0]), p.rank + dir_[1])
                    except Exception:
                        break

                    piece = self.get(p)

                    if not piece:
                        continue
                    if piece.color != turn or piece.type != ptype:
                        break
                    avail.add(p)
                    break
        elif from_.is_partial():
            if from_.file:
                # We will only have two possible position to get to the destination if we're giving the src file
                dist = abs(to.file - from_.file)
                poss = ((from_.file, to.rank + dist), (from_.file, to.rank - dist))
                for pos in poss:
                    if pos[1] <= 0 or pos[1] >= 9:
                        continue
                    f = SquarePosition(pos[0], pos[1])
                    if (
                        not self.get(f)
                        or self.get(f).type != ptype
                        or self.get(f).color != turn
                    ):
                        continue
                    if is_valid_start_pos(f):
                        avail.add(f)

            else:
                # same explaination as above but for ranks
                dist = abs(to.rank - from_.rank)
                files = (dist, 8 - dist)
                for file in files:
                    f = SquarePosition(f, from_.rank)
                    if (
                        not self.get(f)
                        or self.get(f).type != ptype
                        or self.get(f).color != turn
                    ):
                        continue
                    if is_valid_start_pos(f):
                        avail.add(f)

        elif is_valid_start_pos(from_):
            avail.add(from_)

        return list(avail)

    def copy(self):
        newb = Board()
        newb.config = self.config.copy()
        newb.can_castle = self.can_castle.copy()
        newb.en_passant = self.en_passant.copy()
        return newb
