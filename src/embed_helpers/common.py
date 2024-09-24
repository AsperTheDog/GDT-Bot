from enum import Enum


class Difficulty(Enum):
    UNDEFINED = 0
    PARTY = 1
    EASY = 2
    NORMAL = 3
    HARD = 4
    CAMPAIGN = 5


class Platform(Enum):
    UNDEFINED = 0
    PC = 1
    PS4 = 2
    PS5 = 3
    XBOX = 4
    SWITCH = 5


def safeGet(dictionary: dict, paths: list[str] | str, default):
    if not isinstance(paths, list):
        paths = [paths]
    for path in paths:
        val = dictionary
        try:
            for key in path.split("/"):
                if isinstance(val, list):
                    val = val[int(key)]
                else:
                    val = val[key]
            return val
        except (KeyError, ValueError):
            continue
    return default
