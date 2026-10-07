"""Run with: python -m pytest test_poker_equity.py   (or just: python test_poker_equity.py)"""
from poker_equity import *


def hand(text):
    return evaluate(parse_cards(text))


def test_hand_ordering():
    assert hand("AsKsQsJsTs") > hand("9s9h9d9cAs")        # royal > quads
    assert hand("9s9h9d9cAs") > hand("KsKhKdQsQh")        # quads > full house
    assert hand("KsKhKdQsQh") > hand("As9s7s5s2s")        # full house > flush
    assert hand("As9s7s5s2s") > hand("5s4h3d2cAs")        # flush > straight
    assert hand("5s4h3d2cAs") > hand("KsKhKd7c2s")        # wheel straight > trips
    assert hand("KsKhKd7c2s") > hand("AsAhKdKc2s")        # trips < two pair
    assert hand("AsAhKdKc2s") > hand("AsAh9d7c2s")        # two pair > pair
    assert hand("AsAh9d7c2s") > hand("AsKh9d7c2s")        # pair > high card


def test_wheel_is_lowest_straight():
    assert hand("6s5h4d3c2s") > hand("5s4h3d2cAs")


def test_seven_cards_picks_best_five():
    assert hand("AsKsQsJsTs2d3c")[0] == STRAIGHT_FLUSH
    assert hand("KsKhKdQsQh2c3d")[0] == FULL_HOUSE


def test_kickers():
    assert hand("AsAhKd7c2s") > hand("AsAhQd7c2s")


def test_known_equities():
    # Aces vs kings preflop is roughly 82% for aces (the exact value shifts slightly with suits).
    r = simulate(parse_cards("AsAh"), [parse_cards("KdKc")], trials=40_000, seed=1)
    assert abs(r["equity"] - 0.82) < 0.015
    # Ace-king suited vs queens is close to a coin flip (about 46% for AKs).
    r = simulate(parse_cards("AsKs"), [parse_cards("QhQd")], trials=40_000, seed=1)
    assert abs(r["equity"] - 0.46) < 0.02


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("passed:", name)
