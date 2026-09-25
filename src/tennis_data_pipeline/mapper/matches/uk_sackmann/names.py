"""Deterministic (non-fuzzy) Tennis-Data UK <-> Sackmann player-name compatibility."""

from __future__ import annotations

import unicodedata
from typing import NamedTuple


class SourcePlayerName(NamedTuple):
    """A parsed Tennis-Data UK abbreviated name, e.g. "Fritz T." -> ("fritz", "t")."""

    surname: str
    initials: str


# Latin-Extended letters that NFKD does NOT decompose into a base letter + combining
# accent (so plain NFKD + ascii-encode("ignore") would silently delete them instead of
# transliterating them, e.g. "Đoković" -> "okovic"). Mapped explicitly before NFKD.
_NON_DECOMPOSING_LETTERS = str.maketrans(
    {
        "\u0110": "D",
        "\u0111": "d",  # Đ đ
        "\u0141": "L",
        "\u0142": "l",  # Ł ł
        "\u00d8": "O",
        "\u00f8": "o",  # Ø ø
        "\u00d0": "D",
        "\u00f0": "d",  # Ð ð (eth)
        "\u00de": "Th",
        "\u00fe": "th",  # Þ þ (thorn)
        "\u00df": "ss",  # ß
        "\u00c6": "Ae",
        "\u00e6": "ae",  # Æ æ
        "\u0152": "Oe",
        "\u0153": "oe",  # Œ œ
    }
)


def normalize_name(value: str) -> str:
    """Lowercase, strip accents/punctuation (keeping spaces/hyphens) for name comparison."""
    text = str(value).translate(_NON_DECOMPOSING_LETTERS)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = "".join(ch if ch.isalnum() or ch in " -" else " " for ch in text)
    return " ".join(text.split())


def parse_tennis_data_name(value: str) -> SourcePlayerName:
    """Parse a Tennis-Data UK "Surname(s) Initials." name into (surname, initials).

    Initials are identified by a trailing "." on the *original* token (e.g.
    "T.", "Zh.", "J.J.", "J."+"P." are all initials tokens) rather than by
    length, since real surnames can be just as short (e.g. "Wu Y.", "Bu Y.").
    Every trailing dotted token is consumed, so both a single fused token
    ("Wolf J.J." -> initials "jj") and separately spaced initials
    ("Varillas J. P." -> initials "jp") parse correctly, and whatever's left
    (possibly multiple words) is the surname. A name with no dotted trailing
    token at all is treated as a bare surname with no initials.
    """
    tokens = str(value).split()
    surname_tokens = list(tokens)
    initials_tokens: list[str] = []
    while len(surname_tokens) > 1 and surname_tokens[-1].endswith("."):
        initials_tokens.insert(0, surname_tokens.pop().replace(".", ""))
    surname = normalize_name(" ".join(surname_tokens))
    initials = normalize_name("".join(initials_tokens))
    return SourcePlayerName(surname=surname, initials=initials)


def _compact(value: str) -> str:
    """Letters only - spaces/hyphens stripped - so surnames compare equal across
    different word-splitting/hyphenation conventions ("Auger-Aliassime" vs
    "Auger Aliassime", "O Connell" vs "Oconnell")."""
    return value.replace(" ", "").replace("-", "")


def player_name_compatible(source_name: str, canonical_name: str) -> bool:
    """Deterministically check if a Tennis-Data abbreviated name matches a full Sackmann name.

    The parsed surname must match some trailing run of the canonical name's
    tokens once both are compacted to letters-only (no fuzzy/edit-distance
    matching - hyphens/spaces are the only thing treated as equivalent). If
    the source name has initials, they must match the given-name tokens
    immediately preceding the surname: either as a single prefix ("Zh." ->
    "Zhizhen") or one letter per token ("J.P." -> "Juan Pablo", "J.J." ->
    "J J").
    """
    source = parse_tennis_data_name(source_name)
    if not source.surname:
        return False

    canonical_tokens = normalize_name(canonical_name).split(" ")
    source_surname_compact = _compact(source.surname)

    surname_token_count: int | None = None
    for n in range(1, len(canonical_tokens) + 1):
        if _compact("".join(canonical_tokens[-n:])) == source_surname_compact:
            surname_token_count = n
            break
    if surname_token_count is None:
        return False

    if not source.initials:
        return True

    given_tokens = canonical_tokens[: len(canonical_tokens) - surname_token_count]
    if not given_tokens:
        return False

    if given_tokens[0].startswith(source.initials):
        return True
    if len(given_tokens) >= len(source.initials):
        return all(given_tokens[i][:1] == letter for i, letter in enumerate(source.initials))
    return False
