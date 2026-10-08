"""Shared display helpers."""


def star_bar(avg_rating: float) -> str:
    """Render a 1-10 rating as a five-star bar, e.g. ⭐⭐⭐✨☆."""
    star_rating = avg_rating / 2
    full_stars = int(star_rating)
    half_star = 1 if (star_rating - full_stars) >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    return "⭐" * full_stars + ("✨" if half_star else "") + "☆" * empty_stars


def review_stars(rating: int) -> str:
    """Compact stars for a single review (one star per two points)."""
    return "⭐" * (rating // 2) + ("✨" if rating % 2 else "")


def generate_star_rating(avg_rating: float, total_reviews: int) -> str | None:
    if total_reviews == 0:
        return None
    return f"Rating: {star_bar(avg_rating)} ({avg_rating:.1f}/10 from {total_reviews} review{'s' if total_reviews != 1 else ''})"
