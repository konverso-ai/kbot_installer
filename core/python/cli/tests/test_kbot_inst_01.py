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
    """Run another command line and compare both outputs and exit codes, keeping the first result."""
    first = env.result
    assert first is not None
    other = env.run(cmdline)
    env.result = first
    assert (other.output, other.exit_code) == (first.output, first.exit_code)


@then(step("the storage is not read"))
def storage_not_read(env: Environment) -> None:
    """Check the storage provider was never used."""
    assert env.storage.downloads == []
    assert env.storage.reads == []


@then(step('the products downloaded from the "{area}" area of the "{backend}" storage are "{products}"'))
def downloaded_products(env: Environment, area: str, backend: str, products: str) -> None:
    """Check exactly these products were downloaded, all from that backend and area."""
    assert [(d.backend, d.area, d.key.split("/")[1]) for d in env.storage.downloads] == [
        (backend, area, name) for name in names(products)
    ]
