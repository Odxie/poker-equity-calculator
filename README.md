## I built this project two years ago for my poker club in high school. 
It is a Texas Hold'em equity calculator written in Python. It estimates the probability that a hand wins or ties by dealing the unknown cards at random many times, and reports a 95% confidence interval so you can see how precise the estimate is.

## Usage

```bash
python poker_equity.py AsAh KdKc                          # specific hand vs specific hand
python poker_equity.py AsKs QhQd --board Jc7s2d           # with a flop
python poker_equity.py AhKh --opponents 3 --trials 200000 # vs 3 random hands
```

Cards are written rank then suit: `As` = ace of spades, `Td` = ten of diamonds.

Example output:

```
Hero: As Ah
Trials: 100,000
Win:  81.00%   Tie: 0.38%   Lose: 18.63%
Equity: 81.19%  (95% CI: 80.94% to 81.43%)
```

## How it works

- **Hand evaluator:** scores the best 5-card hand out of 7 cards as a tuple `(category, tiebreakers...)`, so hands compare with ordinary `>`.
- **Simulation:** each trial deals the missing board cards (and random opponent hands) from the remaining deck, then scores every player.
- **Accuracy:** the standard error shrinks like 1/sqrt(N), so 100x more trials gives 10x more precision.

## Tests

```bash
python test_poker_equity.py
```

Checks hand rankings(including the A-2-3-4-5 straight)and compares simulated equities with known values.
