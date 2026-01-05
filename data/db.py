import uuid

from core.game import GameState
from db import chessdb

_players = chessdb["players"]
_matches = chessdb["matches"]


class PlayerData:
    def __init__(
        self, user_id, num_matches: int = 0, num_wins: int = 0, num_draws: int = 0
    ):
        self.user_id = user_id
        self.num_matches = num_matches
        self.num_wins = num_wins
        self.num_draws = num_draws
        self.num_losses = num_matches - num_wins - num_draws

    @staticmethod
    def from_dict(d):
        return PlayerData(d["_id"], d["num_matches"], d["num_wins"], d["num_draws"])

    @staticmethod
    def from_id(user_id):
        res = _players.find_one({"_id": user_id}, {})
        if not res:
            return None
        return PlayerData.from_dict(res)

    def insert_to_db(self) -> bool:
        return _players.insert_one(self.__dict__) is not None

    def update_db(self) -> bool:
        d = self.__dict__
        print("yay")
        _id = d.pop("user_id")
        return _players.update_one({"_id": _id}, {"$set": d}, upsert=True).acknowledged


class MatchData:
    def __init__(self, gid: uuid.UUID, played_moves, white_id, black_id, state, turn):
        self.moves_full = list(map(lambda x: str(x[0]), played_moves))
        self.moves_partial = list(map(lambda x: str(x[1]), played_moves))
        self.white = white_id
        self.black = black_id
        self.state = state
        self._id = gid
        self.turn = turn

    def insert_to_db(self) -> bool:
        return _matches.insert_one(self.__dict__).acknowledged

    def update_on_db(self, fields: [str] = []) -> bool:
        d = self.__dict__
        _id = d["_id"]
        upds = {}
        if not fields:
            upds = d.copy()
            upds.pop("_id")  # because you dont really update _id

        # this will run only if fields contain something
        for field in fields:
            upds[field] = d[field]

        return _matches.update_one({"_id": _id}, {"$set": upds}).acknowledged

    @staticmethod
    def from_dict(d):
        m = MatchData(d["_id"], [], d["white"], d["black"], d["state"], d["turn"])
        m.moves_full = d["moves_full"]
        m.moves_partial = d["moves_partial"]
        return m

    def get_from_game_id(_id: uuid.UUID):
        res = _matches.find_one({"_id": _id}, {})
        if not res:
            return None
        return MatchData.from_dict(res)

    def get_active_game_by_userid(user_id: uuid.UUID):
        res = _matches.find_one(
            {
                "state": GameState.Playing,
                "$or": [{"white": user_id}, {"black": user_id}],
            }
        )
        if not res:
            return None
        return MatchData.from_dict(res)


def get_all_running_matches() -> [MatchData]:
    res = _matches.find({"state": GameState.Playing}, {})
    return [MatchData.from_dict(m) for m in res]
