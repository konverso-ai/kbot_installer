"""String conversion between snake_case and PascalCase."""

import re


def pascal2snake(name: str) -> str:
    """Convert a PascalCase string to snake_case.

    Args:
        name: String in PascalCase format.

    Returns:
        String converted to snake_case.

    Example:
        >>> pascal2snake("NexusProvider")
        'nexus_provider'
        >>> pascal2snake("HTTPResponse")
        'http_response'

    """
    if not name:
        return name

    step1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    step2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", step1)
    return step2.replace("-", "_").lower()


def snake2pascal(name: str) -> str:
    """Convert a snake_case string to PascalCase.

    Args:
        name: String in snake_case format.

    Returns:
        String converted to PascalCase.

    Example:
        >>> snake2pascal("nexus_provider")
        'NexusProvider'
        >>> snake2pascal("http_response")
        'HttpResponse'

    """
    if not name:
        return name

    components = [part for part in name.split("_") if part]
    if not components:
        return ""

    return "".join(word.capitalize() for word in components)
