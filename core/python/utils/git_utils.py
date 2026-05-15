import re


def parse_release_branch_name(branch_name: str) -> tuple[int, int, bool] | None:
    """Return the year, sequence, and whether the branch is a dev branch from a release-YYYY.NN branch name.

    Args:
        branch_name: The name of the branch to parse.

    Returns:
        A ``(year, seq, is_dev)`` tuple for the release, or ``None`` if no matching branch exists.
    """
    match = re.match(r"^release-(\d{4})\.(\d+)(-dev)?$", branch_name or "")
    if not match:
        return None
    year = int(match.group(1))
    seq = int(match.group(2))
    is_dev = bool(match.group(3))
    return year, seq, is_dev
