"""Test the features module on synthetic text with known counts."""
import pytest

from provenance import features as F


def test_word_and_sentence_tokens():
    assert F.words("Hello, complexity's world!") == ["Hello", "complexity's", "world"]
    assert F.sentences("One. Two! Three?") == ["One.", "Two!", "Three?"]


def test_emdash_counts_unicode_and_ascii():
    assert F.emdash_count("a — b") == 1
    assert F.emdash_count("a -- b") == 1          # ascii em-dash with word-chars around
    assert F.emdash_count("a - b") == 0           # hyphen, not counted
    assert F.emdash_count("words without dashes") == 0


def test_delve_family_word_boundaries():
    f = F.extract("We delve into it. They delves? no. Delving out.")
    assert f["n_lexicon"]["delve"] == 1
    assert f["n_lexicon"]["delves"] == 1
    assert f["n_lexicon"]["delving"] == 1
    # substring must not match: "delving" contains "delv" but not "delve"
    assert f["n_lexicon"]["delve"] + f["n_lexicon"]["delves"] == 2


def test_not_x_but_y():
    assert len(F.NOT_X_BUT_Y_RE.findall("not a test, but a gift")) == 1
    assert len(F.NOT_X_BUT_Y_RE.findall("Not only speed, but reliability matters")) == 1
    assert len(F.NOT_X_BUT_Y_RE.findall("I like cats but not dogs")) == 0


def test_not_only_but_also():
    text = "Not only the theory but also the practice"
    assert len(F.NOT_ONLY_BUT_RE.findall(text)) == 1
    assert len(F.NOT_ONLY_BUT_RE.findall("not only theory. but also later")) == 0


def test_triad():
    text = "one, two, and three"
    assert len(F.TRIAD_RE.findall(text)) == 1
    assert len(F.TRIAD_RE.findall("one two and three")) == 0


def test_core_slop_excludes_core_lexicon_only_items():
    # "crucial" is in AI_LEXICON but not CORE_SLOP
    f = F.extract("It is crucial and robust.")
    assert f["n_lex"] == 2
    assert f["n_core"] == 1  # only "robust"


def test_stats_and_rates():
    f = F.full("One simple test. Another slightly longer test here — ok?")
    for k in ["emdash_per_1k", "triad_per_1k", "core_per_1k", "ttr",
              "mean_sent_len", "std_sent_len", "mean_word_len", "n_words"]:
        assert k in f
    assert f["n_words"] == 9
    assert f["emdash_per_1k"] == pytest.approx(1 / 9 * 1000)


def test_empty_text_does_not_crash():
    f = F.full("")
    assert f["n_words"] == 0


def test_feature_keys_complete():
    f = F.full("Some text here.")
    for k in F.FEATURE_KEYS:
        assert isinstance(f[k], (int, float))
