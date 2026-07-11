from enum import Enum


class RuleAction(str, Enum):
    LINK = "link"
    COPY = "copy"
    IGNORE = "ignore"
