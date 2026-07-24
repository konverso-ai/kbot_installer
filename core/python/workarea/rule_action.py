"""Actions that a workarea rule can apply to a matched source path."""

from enum import Enum


class RuleAction(str, Enum):
    """Action applied to a source path when laying out the workarea.

    Attributes:
        LINK: Create a symlink from the workarea target to the product source.
        COPY: Copy the product source into the workarea target, optionally
            rendering placeholder variables.
        IGNORE: Skip the source path entirely.

    """

    LINK = "link"
    COPY = "copy"
    IGNORE = "ignore"
