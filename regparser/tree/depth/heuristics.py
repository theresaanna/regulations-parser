"""Set of heuristics for trimming down the set of solutions. Each heuristic
works by penalizing a solution; it's then up to the caller to grab the
solution with the least penalties."""
from collections import defaultdict
from itertools import takewhile


def prefer_multiple_children(solutions, weight=1.0):
    """Dock solutions which have a paragraph with exactly one child. While
    this is possible, it's unlikely."""
    result = []
    for solution in solutions:
        flags = 0
        depths = [a.depth for a in solution.assignment]
        for i, depth in enumerate(depths):
            children = takewhile(lambda d: d > depth, depths[i+1:])
            if len(filter(lambda d: d == depth + 1, children)) == 1:
                flags += 1
        result.append(solution.copy_with_penalty(weight * flags / len(depths)))
    return result


def prefer_diff_types_diff_levels(solutions, weight=1.0):
    """Dock solutions which have different markers appearing at the same
    level. This also occurs, but not often."""
    result = []
    for solution in solutions:
        depth_types = defaultdict(set)
        for par in solution.assignment:
            depth_types[par.depth].add(par.typ)

        flags, total = 0, 0
        for types in depth_types.values():
            total += len(types)
            flags += len(types) - 1

        result.append(solution.copy_with_penalty(weight * flags / total))
    return result


def prefer_shallow_depths(solutions, weight=0.1):
    """Dock solutions which have a higher maximum depth"""
    # Smallest maximum depth across solutions
    min_max_depth = min(max(p.depth for p in s.assignment) for s in solutions)
    max_max_depth = max(p.depth for s in solutions for p in s.assignment)
    variance = max_max_depth - min_max_depth
    if variance:
        result = []
        for solution in solutions:
            max_depth = max(p.depth for p in solution.assignment)
            flags = max_depth - min_max_depth
            result.append(solution.copy_with_penalty(
                weight * flags / variance))
        return result
    else:
        return solutions
