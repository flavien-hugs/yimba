"""Which districts of Côte d'Ivoire a text talks about, from the names of the districts, regions and main towns."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# The 14 districts, in the order of the schematic map of the interface.
DISTRICTS: tuple[str, ...] = (
    "Denguélé",
    "Savanes",
    "Zanzan",
    "Woroba",
    "Vallée du Bandama",
    "Montagnes",
    "Sassandra-Marahoué",
    "Yamoussoukro",
    "Lacs",
    "Comoé",
    "Bas-Sassandra",
    "Gôh-Djiboua",
    "Lagunes",
    "Abidjan",
)

# Names that are also common words: only counted when written with a capital ("Man", not "man").
_CAPITALIZED = {"Man", "Plateau", "Lacs", "Kong", "Kani"}

_PLACES: dict[str, tuple[str, ...]] = {
    "Abidjan": (
        "Abidjan, Cocody, Yopougon, Yopougon, Abobo, Adjamé, Plateau, Marcory, Treichville, Koumassi, Port-Bouët, "
        "Attécoubé, Bingerville, Songon, Anyama, Riviera, Angré, Deux-Plateaux"
    ).split(", "),
    "Lagunes": (
        "Lagunes, Dabou, Grand-Lahou, Jacqueville, Agboville, Adzopé, Akoupé, Alépé, Sikensi, Tiassalé, Taabo"
    ).split(", "),
    "Bas-Sassandra": (
        "Bas-Sassandra, San-Pédro, San Pedro, Sassandra, Soubré, Tabou, Méagui, Buyo, Gueyo, Grand-Béréby"
    ).split(", "),
    "Gôh-Djiboua": "Gôh-Djiboua, Gôh, Gagnoa, Divo, Lakota, Oumé, Guibéroua, Ouragahio".split(", "),
    "Sassandra-Marahoué": "Sassandra-Marahoué, Marahoué, Daloa, Bouaflé, Issia, Sinfra, Zuénoula, Vavoua".split(", "),
    "Montagnes": (
        "Montagnes, Man, Danané, Duékoué, Guiglo, Bangolo, Facobly, Kouibly, Biankouma, Zouan-Hounien, Toulépleu"
    ).split(", "),
    "Lacs": (
        "Lacs, Toumodi, Tiébissou, Dimbokro, Bocanda, Daoukro, M'Bahiakro, Bongouanou, Arrah, Didiévi, Djékanou"
    ).split(", "),
    "Yamoussoukro": "Yamoussoukro, Yakro".split(", "),
    "Vallée du Bandama": "Vallée du Bandama, Bouaké, Katiola, Béoumi, Sakassou, Dabakala".split(", "),
    "Savanes": "Savanes, Korhogo, Ferkessédougou, Boundiali, Ouangolodougou, Tengréla, Sinématiali, Kong".split(", "),
    "Denguélé": "Denguélé, Odienné, Minignan, Madinani, Séguélon".split(", "),
    "Woroba": "Woroba, Séguéla, Touba, Mankono, Kani, Worofla, Dianra".split(", "),
    "Zanzan": "Zanzan, Bondoukou, Bouna, Tanda, Nassian, Doropo, Téhini".split(", "),
    "Comoé": "Comoé, Abengourou, Agnibilékrou, Aboisso, Adiaké, Grand-Bassam, Bassam, Bonoua, Tiapoum".split(", "),
}


def _fold(text: str) -> str:
    """Lower case, no accents, plain apostrophes and dashes: "Gôh-Djiboua" and "goh djiboua" match."""
    plain = unicodedata.normalize("NFKD", text.replace("’", "'")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[-\s]+", " ", plain.lower())


@lru_cache(maxsize=1)
def _patterns() -> dict[str, tuple[re.Pattern[str], re.Pattern[str] | None]]:
    """For each district: a pattern over the folded text, and one over the original text for the capitalized names."""
    compiled = {}
    for district, names in _PLACES.items():
        free = sorted({_fold(name) for name in names if name not in _CAPITALIZED}, key=len, reverse=True)
        strict = sorted({name for name in names if name in _CAPITALIZED}, key=len, reverse=True)
        compiled[district] = (
            re.compile(r"(?<![a-z])(?:" + "|".join(map(re.escape, free)) + r")(?![a-z])"),
            (
                re.compile(r"(?<![A-Za-zÀ-ÿ])(?:" + "|".join(map(re.escape, strict)) + r")(?![A-Za-zÀ-ÿ])")
                if strict
                else None
            ),
        )
    return compiled


def districts_in(text: str) -> frozenset[str]:
    """The districts named in a text (a district, a region or one of its main towns)."""
    folded = _fold(text)
    found = set()
    for district, (free, strict) in _patterns().items():
        if free.search(folded) or (strict and strict.search(text)):
            found.add(district)
    return frozenset(found)
