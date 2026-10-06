import pytest

from tests.conftest import NOW
from yimba.modules.watches.domain.model import AlertThreshold, Frequency, Watch
from yimba.shared.errors import InvalidInput
from yimba.shared.source import SourceKind


def make(**overrides):
    values = dict(
        owner_id="u1",
        name="  Santé   et vaccination ",
        keywords=["vaccin", " vaccin ", "santé  publique", ""],
        sources=[SourceKind.FACEBOOK, SourceKind.NEWS, SourceKind.FACEBOOK],
        now=NOW,
    )
    values.update(overrides)
    return Watch.create(**values)


def test_create_normalizes_input():
    watch = make()
    assert watch.name == "Santé et vaccination"
    assert watch.slug == "sante-et-vaccination"
    assert watch.keywords == ("vaccin", "santé publique")
    assert watch.sources == (SourceKind.FACEBOOK, SourceKind.NEWS)
    assert watch.languages == ("fr",) and watch.countries == ("CI",)


@pytest.mark.parametrize(
    "overrides",
    [{"name": "  "}, {"keywords": ["", " "]}, {"sources": []}, {"keywords": [f"k{i}" for i in range(21)]}],
)
def test_create_rejects_invalid_watches(overrides):
    with pytest.raises(InvalidInput):
        make(**overrides)


def test_frequency_and_threshold_are_validated():
    with pytest.raises(InvalidInput):
        Frequency(7)
    with pytest.raises(InvalidInput):
        AlertThreshold(negative_share=0)
    with pytest.raises(InvalidInput):
        AlertThreshold(min_mentions=0)


def test_revise_is_atomic_when_invalid():
    watch = make()
    with pytest.raises(InvalidInput):
        watch.revise(now=NOW, name="Autre nom", keywords=[])
    assert watch.name == "Santé et vaccination"


def test_revise_updates_slug_and_timestamp():
    watch = make()
    later = NOW.replace(hour=15)
    watch.revise(now=later, name="Emploi des jeunes", active=False)
    assert (watch.slug, watch.active, watch.updated_at) == ("emploi-des-jeunes", False, later)
