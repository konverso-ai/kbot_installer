"""WorkareaUpdatable: update or repair a Workarea, then relink its products."""

from installable.workarea_installable import WorkareaInstallable
from updatable.factory import UpdatableName, add_updatable


class WorkareaUpdatable:
    """Dispatch an update or repair of a `Workarea`, then reinstall it.

    `SMOOTH` requires no preparation (nothing to clear, no broken links to remove).
    Every other mode first runs the strategy matching `mode` (clearing the workarea,
    removing broken symlinks, etc.). In every case, `installable.install()` is then
    called to re-apply the workarea rules for every product currently present under
    the installer root, so products added or changed since the last update are picked
    up.

    Attributes:
        installable: The `WorkareaInstallable` to update or repair.
        mode: Updatable strategy to run (see `updatable.factory.UpdatableName`).

    """

    def __init__(self, installable: WorkareaInstallable, mode: UpdatableName) -> None:
        """Bind the dispatcher to the installable and strategy it will run.

        Args:
            installable: The `WorkareaInstallable` to update or repair.
            mode: Updatable strategy to run.

        """
        self.installable = installable
        self.mode = mode

    def __call__(self) -> None:
        """Run the strategy named by `mode` (skipped for `SMOOTH`), then reinstall."""
        if self.mode != UpdatableName.SMOOTH:
            updatable = add_updatable(name=self.mode.value, workarea=self.installable.workarea)
            updatable()

        self.installable.install()
