"""What people talk about: the words that come back in the most conversations, and what they say about them."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

from yimba.modules.analysis.public import SentimentLabel

_URL = re.compile(r"https?://\S+|www\.\S+")
_WORD = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’-]{3,}")
_STOPWORDS = frozenset(
    """
    ainsi alors apres assez aucun aucune aupres aussi autre autres avant avec avoir beaucoup bien cela celle celles
    celui cent cependant certains cette ceux chaque chez comme comment contre dans depuis dernier dernieres derniers
    dont donc doit doivent elle elles encore enfin entre etait etaient etant etre faire fait faut font hier ici ils
    jamais jusqu jusque leur leurs lors maintenant mais meme merci moins mois nous nouveau notre nos oui parce pendant
    peut peuvent plus plusieurs pour pourquoi pourtant puis quand quel quelle quelles quels quelque quelques sans
    selon sera seront serait ses seulement sont sous souvent sur tant tellement tous tout toute toutes tres trop trois
    une vont votre vos voici voila vous aujourd hui deja tjrs
    about after also been before being between both could does done each from have here into just like make more most
    much only other over same should some such than that their them then there these they this those very want were
    what when where which while will with would your
    http https www com html
    """.split()
)


def _fold(word: str) -> str:
    plain = unicodedata.normalize("NFKD", word.replace("’", "'")).encode("ascii", "ignore").decode("ascii")
    return plain.lower().strip("'-")


@dataclass(frozen=True, slots=True)
class Theme:
    term: str
    mentions: int
    negative: int
    neutral: int
    positive: int


def top_terms(
    rows: Iterable[tuple[str, SentimentLabel]],
    exclude: Sequence[str] = (),
    limit: int = 6,
    min_mentions: int = 3,
) -> list[Theme]:
    """The ``limit`` words found in the most conversations (once per conversation), words of the watch left out.

    ``exclude`` takes the keywords of the watch: they are in nearly every conversation and tell nothing.
    """
    skipped = set(_STOPWORDS)
    for phrase in exclude:
        skipped.update(_fold(word) for word in _WORD.findall(phrase))
    seen: Counter[str] = Counter()
    spelled: dict[str, Counter[str]] = {}
    by_label: dict[str, Counter[SentimentLabel]] = {}
    for text, label in rows:
        terms = {}
        for word in _WORD.findall(_URL.sub(" ", text)):
            key = _fold(word)
            if len(key) >= 4 and key not in skipped:
                terms.setdefault(key, word.lower())
        for key, spelling in terms.items():
            seen[key] += 1
            spelled.setdefault(key, Counter())[spelling] += 1
            by_label.setdefault(key, Counter())[label] += 1
    ranked = [(key, count) for key, count in seen.most_common() if count >= min_mentions]
    return [
        Theme(
            term=spelled[key].most_common(1)[0][0],
            mentions=count,
            negative=by_label[key][SentimentLabel.NEGATIVE],
            neutral=by_label[key][SentimentLabel.NEUTRAL],
            positive=by_label[key][SentimentLabel.POSITIVE],
        )
        for key, count in ranked[:limit]
    ]
