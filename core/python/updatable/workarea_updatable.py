"""WorkareaUpdatable: update or repair a Workarea using its configured strategy."""

from updatable.factory import UpdatableName, add_updatable
from workarea.workarea import Workarea


class WorkareaUpdatable:
    """Dispatch an update or repair of a `Workarea` to the matching updatable strategy.

    `SMOOTH` requires no preparation (nothing to clear, no broken links to remove), so
    it is a no-op. Every other mode runs the strategy matching `mode` (clearing the
    workarea, removing broken symlinks, etc.).

    Attributes:
        workarea: The `Workarea` model to update or repair.
        mode: Updatable strategy to run (see `updatable.factory.UpdatableName`).

    """

    def __init__(self, workarea: Workarea, mode: UpdatableName) -> None:
        """Bind the dispatcher to the workarea and strategy it will run.

        Args:
            workarea: The `Workarea` model to update or repair.
            mode: Updatable strategy to run.

        """
        self.workarea = workarea
        self.mode = mode

    def __call__(self) -> None:
        """Run the strategy named by `mode`, or do nothing for `SMOOTH`."""
        if self.mode == UpdatableName.SMOOTH:
            return

        updatable = add_updatable(name=self.mode.value, workarea=self.workarea)
        updatable()
