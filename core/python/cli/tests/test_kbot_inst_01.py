"""PO sheet KBOT-INST-01 — Product download and listing: steps used by this sheet only."""

from pathlib import Path

from pytest_bdd import given, scenarios, then

from cli import commands
from cli.tests.bdd.steps_common import names, step
from cli.tests.bdd.environment import Environment

scenarios("features/KBOT-INST-01.feature")


@given(step('the command "{command}" fails outside its own error handling with "{message}"'))
def command_fails(env: Environment, command: str, message: str) -> None:
    """Make a command raise an error its own try/except never sees."""

    def fail(**_: object) -> None:
        """Raise the unexpected error."""
        raise RuntimeError(message)

    env.monkeypatch.setattr(commands.cli.commands[command], "callback", fail)


@given(
    step(
        'the storage holds the product "{name}" version "{version}" at commit "{commit}" of branch "{branch}" '
        "without a description.xml"
    )
)
def storage_product_without_xml(env: Environment, name: str, version: str, commit: str, branch: str) -> None:
    """Publish a product archive that lacks its description.xml."""
    env.storage.publish_product(name, version, branch, commit, with_description_xml=False)


@given(step('reading the directory "{path}" fails with "{message}"'))
def unreadable_directory(env: Environment, path: str, message: str) -> None:
    """Make listing a directory fail, whoever runs the tests (root ignores file modes)."""
    target = env.path(path)
    target.mkdir(parents=True, exist_ok=True)
    iterdir = Path.iterdir

    def failing_iterdir(self: Path) -> object:
        """Fail on the target directory only."""
        if self == target:
            raise PermissionError(13, message, str(self))
        return iterdir(self)

    env.monkeypatch.setattr(Path, "iterdir", failing_iterdir)


@then(step('the output is the same as for "{cmdline}"'))
def same_output(env: Environment, cmdline: str) -> None:
    """Run another command line and compare both outputs."""
    assert env.result is not None
    first = env.result
    assert env.run(cmdline).output == first.output


@then(step("the storage is not read"))
def storage_not_read(env: Environment) -> None:
    """Check the storage provider was never used."""
    assert env.storage.downloads == []
    assert env.storage.reads == []


@then(step("the git providers are tried in order:"))
def git_providers_order(env: Environment, datatable: list[list[str]]) -> None:
    """Check the order in which the git providers were contacted."""
    tried = list(dict.fromkeys(provider for provider, _ in env.git.attempts))
    assert tried == [row[0] for row in datatable[1:]]


@then(step('the product "{name}" is downloaded from the "{area}" area of the "{backend}" storage'))
def downloaded_from_area(env: Environment, name: str, area: str, backend: str) -> None:
    """Check which storage backend and area the product archive came from."""
    sources = {(d.backend, d.area) for d in env.storage.downloads if d.key.split("/")[1] == name}
    assert sources == {(backend, area)}, sources


@then(step('the products downloaded from the "{area}" area of the "{backend}" storage are "{products}"'))
def downloaded_products(env: Environment, area: str, backend: str, products: str) -> None:
    """Check exactly these products were downloaded, all from that backend and area."""
    assert [(d.backend, d.area, d.key.split("/")[1]) for d in env.storage.downloads] == [
        (backend, area, name) for name in names(products)
    ]
