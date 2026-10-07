from yimba.modules.analysis.public import SentimentLabel
from yimba.modules.mentions.domain.places import DISTRICTS, districts_in
from yimba.modules.mentions.domain.themes import top_terms

NEG, NEU, POS = SentimentLabel.NEGATIVE, SentimentLabel.NEUTRAL, SentimentLabel.POSITIVE


def test_a_text_names_the_districts_of_its_towns():
    assert districts_in("Rupture de doses au centre de santé de Korhogo") == {"Savanes"}
    assert districts_in("Coupures d'eau à Yopougon et à Daloa") == {"Abidjan", "Sassandra-Marahoué"}
    assert districts_in("on est à san pedro depuis lundi") == {"Bas-Sassandra"}
    assert districts_in("Rien dans le Gôh-Djiboua, ni à GOH DJIBOUA") == {"Gôh-Djiboua"}
    assert districts_in("Les doses n'arrivent pas dans la Vallée du Bandama") == {"Vallée du Bandama"}


def test_names_that_are_also_words_need_a_capital_and_a_whole_word():
    assert districts_in("Les gens de Man attendent") == {"Montagnes"}
    assert districts_in("a man said the plateau was empty, just like many lacs") == set()
    assert districts_in("Manifestation à Abidjan") == {"Abidjan"}  # "Man" is not the start of "Manifestation"
    assert districts_in("Il y a un vaccin pour tous") == set()


def test_the_district_list_is_the_fourteen_districts():
    assert len(DISTRICTS) == len(set(DISTRICTS)) == 14
    for district in DISTRICTS:
        if district != "Lacs":  # a capital-only name, found in "les Lacs"
            assert district in districts_in(f"dans le district de {district}")
    assert districts_in("dans les Lacs") == {"Lacs"}


def test_themes_count_conversations_not_repetitions():
    rows = [
        ("Les doses manquent, doses doses", NEG),
        ("Pas de doses au centre de santé", NEG),
        ("Les doses sont arrivées merci", POS),
        ("Le centre de santé est fermé", NEU),
        ("Centre ouvert, vaccination gratuite", POS),
        ("https://example.org/centre-vaccination rien", NEU),
    ]
    themes = top_terms(rows, exclude=["vaccination"], min_mentions=2)
    # A word counts once per conversation, however often it is repeated; the link in the last one is ignored.
    assert {(t.term, t.mentions) for t in themes} == {("doses", 3), ("centre", 3), ("santé", 2)}
    by_term = {t.term: t for t in themes}
    assert by_term["doses"].mentions == 3 and (by_term["doses"].negative, by_term["doses"].positive) == (2, 1)
    assert "vaccination" not in by_term and "example" not in by_term and "https" not in by_term
    assert "pour" not in by_term and "les" not in by_term


def test_themes_need_a_minimum_and_ignore_accents_in_grouping():
    rows = [("Épidémie à craindre", NEG), ("epidemie en hausse", NEG), ("Une épidémie ?", NEU), ("autre chose", NEU)]
    (theme,) = top_terms(rows, min_mentions=3)
    assert theme.term == "épidémie" and theme.mentions == 3 and theme.negative == 2
    assert top_terms(rows, min_mentions=4) == []


def test_elided_articles_and_the_country_are_not_themes():
    rows = [
        ("L'opposition réclame une réforme en Côte d'Ivoire", NEG),
        ("Les partis de l'opposition rencontrent le gouvernement", NEU),
        ("Qu'en pense l’opposition ? Côte d’Ivoire", NEG),
    ]
    themes = top_terms(rows, min_mentions=3)
    assert [t.term for t in themes] == ["opposition"]


def test_a_plural_counts_with_its_singular():
    rows = [("Une proposition", NEU), ("Des propositions", NEU), ("Ses propositions", NEG), ("Nouvelle loi", NEU)]
    themes = top_terms(rows, min_mentions=3)
    assert [(t.term, t.mentions, t.negative) for t in themes] == [("propositions", 3, 1)]
