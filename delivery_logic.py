"""Pure delivery rules shared by the route and its focused test."""


def split_delivery(text: str, maximum_words: int = 80) -> list[str]:
    """Keep a creator's sentences together while staying inside a compact segment."""
    words = text.split()
    return [" ".join(words[index:index + maximum_words]) for index in range(0, len(words), maximum_words)]
