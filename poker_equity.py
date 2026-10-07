"""
Monte Carlo poker equity calculator (Texas Hold'em).

Estimates the probability that your hand wins (or ties) against one or more
opponents by dealing the unknown cards at random many times and counting results.

Examples:
    python poker_equity.py AsAh KsKh
    python poker_equity.py AsKs QhQd --board Jc7s2d
    python poker_equity.py AhKh --opponents 3 --trials 200000
"""

import argparse
import math
import random
from collections import Counter
from itertools import combinations

RANKS = "23456789TJQKA"
SUITS = "cdhs"

# Hand categories, higher is better.
HIGH_CARD, PAIR, TWO_PAIR, TRIPS, STRAIGHT, FLUSH, FULL_HOUSE, QUADS, STRAIGHT_FLUSH = range(9)
CATEGORY_NAMES = [
    "High Card", "Pair", "Two Pair", "Three of a Kind", "Straight",
    "Flush", "Full House", "Four of a Kind", "Straight Flush",
]


# ---------- Cards ----------
# A card is an int 0..51: rank = card // 4 (0 = deuce ... 12 = ace), suit = card % 4.

def parse_card(text: str) -> int:
    """Convert 'As' or 'Td' into an int 0..51."""
    text = text.strip()
    if len(text) != 2 or text[0].upper() not in RANKS or text[1].lower() not in SUITS:
        raise ValueError(f"Invalid card: {text!r} (use e.g. 'As', 'Td', '7c')")
    return RANKS.index(text[0].upper()) * 4 + SUITS.index(text[1].lower())


def parse_cards(text: str) -> list[int]:
    """Parse a string like 'AsKh' or 'As Kh' into a list of cards."""
    text = text.replace(" ", "").replace(",", "")
    if len(text) % 2 != 0:
        raise ValueError(f"Could not parse cards from {text!r}")
    return [parse_card(text[i:i + 2]) for i in range(0, len(text), 2)]


def card_str(card: int) -> str:
    return RANKS[card // 4] + SUITS[card % 4]


# ---------- Hand evaluation ----------

def _straight_high(rank_set: set[int]) -> int | None:
    """Return the high card rank of the best straight in rank_set, or None."""
    ranks = set(rank_set)
    if 12 in ranks:          # an ace can also play low (A-2-3-4-5)
        ranks.add(-1)
    for high in range(12, 2, -1):
        if all((high - i) in ranks for i in range(5)):
            return high
    return None


def evaluate(cards: list[int]) -> tuple:
    """
    Score the best 5-card hand from 5 to 7 cards.
    Returns a tuple that compares correctly with > and <:
    (category, tiebreaker ranks...). Higher is better.
    """
    ranks = [c // 4 for c in cards]
    suits = [c % 4 for c in cards]
    rank_counts = Counter(ranks)

    # Flush / straight flush
    suit_counts = Counter(suits)
    flush_suit = next((s for s, n in suit_counts.items() if n >= 5), None)
    if flush_suit is not None:
        flush_ranks = sorted((r for r, s in zip(ranks, suits) if s == flush_suit), reverse=True)
        sf_high = _straight_high(set(flush_ranks))
        if sf_high is not None:
            return (STRAIGHT_FLUSH, sf_high)

    # Group ranks by how many times they appear, biggest groups first.
    groups = sorted(rank_counts.items(), key=lambda rc: (rc[1], rc[0]), reverse=True)
    counts = [n for _, n in groups]

    if counts[0] == 4:
        quad = groups[0][0]
        kicker = max(r for r in rank_counts if r != quad)
        return (QUADS, quad, kicker)

    if counts[0] == 3 and len(counts) > 1 and counts[1] >= 2:
        return (FULL_HOUSE, groups[0][0], groups[1][0])

    if flush_suit is not None:
        return (FLUSH, *flush_ranks[:5])

    straight_high = _straight_high(set(ranks))
    if straight_high is not None:
        return (STRAIGHT, straight_high)

    if counts[0] == 3:
        trips = groups[0][0]
        kickers = sorted((r for r in rank_counts if r != trips), reverse=True)[:2]
        return (TRIPS, trips, *kickers)

    if counts[0] == 2 and len(counts) > 1 and counts[1] == 2:
        pairs = sorted((r for r, n in rank_counts.items() if n == 2), reverse=True)[:2]
        kicker = max(r for r in rank_counts if r not in pairs)
        return (TWO_PAIR, *pairs, kicker)

    if counts[0] == 2:
        pair = groups[0][0]
        kickers = sorted((r for r in rank_counts if r != pair), reverse=True)[:3]
        return (PAIR, pair, *kickers)

    return (HIGH_CARD, *sorted(ranks, reverse=True)[:5])


# ---------- Monte Carlo simulation ----------

def simulate(hero, villains=None, board=None, num_random_opponents=0,
             trials=100_000, seed=None):
    """
    Estimate hero's equity.

    hero: list of 2 cards
    villains: list of known opponent hands (each a list of 2 cards)
    board: 0-5 known community cards
    num_random_opponents: extra opponents who get random hole cards each trial
    Returns a dict of results.
    """
    rng = random.Random(seed)
    villains = villains or []
    board = board or []

    known = hero + board + [c for v in villains for c in v]
    if len(set(known)) != len(known):
        raise ValueError("Duplicate cards: each card can only appear once.")
    if len(hero) != 2 or any(len(v) != 2 for v in villains):
        raise ValueError("Each player needs exactly 2 hole cards.")
    if len(board) > 5:
        raise ValueError("The board has at most 5 cards.")

    deck = [c for c in range(52) if c not in set(known)]
    board_needed = 5 - len(board)
    cards_to_draw = board_needed + 2 * num_random_opponents

    wins = ties = losses = 0
    equity_sum = 0.0
    equity_sq_sum = 0.0  # for the standard error
    hero_categories = Counter()

    for _ in range(trials):
        drawn = rng.sample(deck, cards_to_draw)
        full_board = board + drawn[:board_needed]
        random_hands = [drawn[board_needed + 2 * i: board_needed + 2 * i + 2]
                        for i in range(num_random_opponents)]

        hero_score = evaluate(hero + full_board)
        hero_categories[hero_score[0]] += 1
        opp_scores = [evaluate(h + full_board) for h in villains + random_hands]
        best_opp = max(opp_scores)

        if hero_score > best_opp:
            wins += 1
            share = 1.0
        elif hero_score == best_opp:
            ties += 1
            tied_players = 1 + sum(1 for s in opp_scores if s == hero_score)
            share = 1.0 / tied_players
        else:
            losses += 1
            share = 0.0
        equity_sum += share
        equity_sq_sum += share * share

    equity = equity_sum / trials
    variance = max(equity_sq_sum / trials - equity ** 2, 0.0)
    std_error = math.sqrt(variance / trials)

    return {
        "trials": trials,
        "win": wins / trials,
        "tie": ties / trials,
        "lose": losses / trials,
        "equity": equity,
        "std_error": std_error,
        "ci95": (equity - 1.96 * std_error, equity + 1.96 * std_error),
        "hero_categories": {CATEGORY_NAMES[k]: v / trials
                            for k, v in sorted(hero_categories.items(), reverse=True)},
    }


# ---------- Command line ----------

def main():
    parser = argparse.ArgumentParser(description="Monte Carlo Texas Hold'em equity calculator.")
    parser.add_argument("hero", help="Your hole cards, e.g. AsKh")
    parser.add_argument("villains", nargs="*", help="Known opponent hands, e.g. QcQd")
    parser.add_argument("--board", default="", help="Known board cards, e.g. Jc7s2d")
    parser.add_argument("--opponents", type=int, default=0,
                        help="Number of additional random-hand opponents")
    parser.add_argument("--trials", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=None, help="Set for reproducible results")
    args = parser.parse_args()

    hero = parse_cards(args.hero)
    villains = [parse_cards(v) for v in args.villains]
    board = parse_cards(args.board) if args.board else []

    if not villains and args.opponents == 0:
        args.opponents = 1  # default: one random opponent

    result = simulate(hero, villains, board, args.opponents, args.trials, args.seed)

    print(f"Hero: {' '.join(card_str(c) for c in hero)}"
          + (f"   Board: {' '.join(card_str(c) for c in board)}" if board else ""))
    print(f"Trials: {result['trials']:,}")
    print(f"Win:  {result['win']:.2%}   Tie: {result['tie']:.2%}   Lose: {result['lose']:.2%}")
    lo, hi = result["ci95"]
    print(f"Equity: {result['equity']:.2%}  (95% CI: {lo:.2%} to {hi:.2%})")
    print("Hero's final hand distribution:")
    for name, p in result["hero_categories"].items():
        print(f"  {name:<16}{p:.2%}")


if __name__ == "__main__":
    main()
