from typing import Sequence


def levenshtein(
    splits: Sequence,
    controls: Sequence,
    insert_cost: int = 1,
    delete_cost: int = 1,
    replace_cost: int = 1,
) -> int:
    """
    Calculate the Levenshtein distance between two sequences.

    Args:
        splits (Sequence): The first sequence. Used for user splits.
        controls (Sequence): The second sequence. Used for course controls.
        insert_cost (int, optional): The cost of inserting a character. Defaults to 1.
        delete_cost (int, optional): The cost of deleting a character. Defaults to 1.
        replace_cost (int, optional): The cost of replacing a character. Defaults to 1.

    Returns:
        int: The Levenshtein distance between the two sequences.
    """
    if len(splits) == 0:
        return len(controls) * insert_cost
    if len(controls) == 0:
        return len(splits) * delete_cost

    costs = (insert_cost, delete_cost, replace_cost)

    if splits[-1] == controls[-1]:
        return levenshtein(splits[:-1], controls[:-1], *costs)

    substitution = levenshtein(splits[:-1], controls[:-1], *costs) + replace_cost
    insertion = levenshtein(splits, controls[:-1], *costs) + insert_cost
    deletion = levenshtein(splits[:-1], controls, *costs) + delete_cost

    return min(substitution, insertion, deletion)
