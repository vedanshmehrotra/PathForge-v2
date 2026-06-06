DIFFICULTY_RATINGS = {
    "Easy": 900,
    "Medium": 1200,
    "Hard": 1500,
}

K_FACTORS = {
    "Easy": 32,
    "Medium": 24,
    "Hard": 16,
}

MIN_ELO = 400.0


def get_problem_rating(difficulty):
    """Return the Elo-equivalent opponent rating for a problem difficulty."""
    try:
        return DIFFICULTY_RATINGS[difficulty]
    except KeyError as exc:
        raise ValueError(f"Unsupported difficulty: {difficulty}") from exc


def get_k_factor(difficulty):
    """Return the Elo K-factor for a problem difficulty."""
    try:
        return K_FACTORS[difficulty]
    except KeyError as exc:
        raise ValueError(f"Unsupported difficulty: {difficulty}") from exc


def calculate_expected(player_rating, opponent_rating):
    """Calculate the standard Elo expected score for player versus opponent."""
    return 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))


def update_elo(current_rating, difficulty, outcome):
    """Return the updated Elo rating for a 1.0, 0.5, or 0.0 submission outcome."""
    if outcome not in (0, 0.0, 0.5, 1, 1.0):
        raise ValueError("outcome must be 1.0, 0.5, or 0.0")

    opponent_rating = get_problem_rating(difficulty)
    expected = calculate_expected(current_rating, opponent_rating)
    updated = current_rating + get_k_factor(difficulty) * (float(outcome) - expected)
    return round(max(MIN_ELO, updated), 2)


def outcome_from_submission(verdict, detected_pattern, expected_pattern):
    """Map a verdict and pattern match into win, partial win, or loss outcome."""
    if verdict not in ("pass", "fail"):
        raise ValueError("verdict must be 'pass' or 'fail'")
    if verdict == "fail":
        return 0.0
    return 1.0 if detected_pattern == expected_pattern else 0.5
