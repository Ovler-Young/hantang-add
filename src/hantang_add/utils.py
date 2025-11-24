import difflib


def word_level_diff(old_text, new_text):
    """Generate word-level diff with markdown formatting."""
    # Convert to string and strip whitespace
    old_str = str(old_text).strip()
    new_str = str(new_text).strip()

    # If exactly equal after normalization, just return the value
    if old_str == new_str:
        return old_str

    # For semicolon-separated values (like tags), compare as sets
    if ";" in old_str and ";" in new_str:
        old_items = [item.strip() for item in old_str.split(";")]
        new_items = [item.strip() for item in new_str.split(";")]

        old_set = set(old_items)
        new_set = set(new_items)

        removed = old_set - new_set
        added = new_set - old_set
        common = old_set & new_set

        if removed or added:
            result_parts = []
            # Show common items first
            result_parts.extend(sorted(common))
            # Show removed items with strikethrough
            result_parts.extend([f"~~{item}~~" for item in sorted(removed)])
            # Show added items in bold
            result_parts.extend([f"**{item}**" for item in sorted(added)])
            return "; ".join(result_parts)

    # For regular text, do word-level diff
    old_words = old_str.split()
    new_words = new_str.split()

    diff = difflib.SequenceMatcher(None, old_words, new_words)
    result = []

    for tag, i1, i2, j1, j2 in diff.get_opcodes():
        if tag == "equal":
            result.extend(old_words[i1:i2])
        elif tag == "delete":
            result.extend([f"~~{word}~~" for word in old_words[i1:i2]])
        elif tag == "insert":
            result.extend([f"**{word}**" for word in new_words[j1:j2]])
        elif tag == "replace":
            result.extend([f"~~{word}~~" for word in old_words[i1:i2]])
            result.extend([f"**{word}**" for word in new_words[j1:j2]])

    return " ".join(result)
