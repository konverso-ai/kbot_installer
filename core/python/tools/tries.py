"""Manual scratch script for exercising workarea install/update flows."""  # noqa: INP001

from installable.updater.factory import UpdaterName


def main() -> None:
    """Build a sample Workarea and run install/update against it."""
    from pathlib import Path  # noqa: PLC0415

    from installable.workarea_installable import WorkareaInstallable  # noqa: PLC0415
    from workarea.workarea import Workarea  # noqa: PLC0415
    from workarea.workarea_rule import WorkareaRules  # noqa: PLC0415

    rules = WorkareaRules.from_json(Path("conf/rules.json").read_text())
    wa = WorkareaInstallable(
        workarea=Workarea(
            installer_root=Path("/tmp/dev/installer"),
            work_root=Path("/tmp/dev/work"),
            products=[
                Path(x)
                for x in (
                    "vm-qa202503dev-we-d.konverso.ai",
                    "kbot-latest-dev",
                    "snow",
                    "kbot",
                    # "kbot-latest-dev", "kbot-latest-dev", "kkeys",
                    # "kbot", "3rdparty", "agentic-saas", "bitbucket",
                    # "jira", "ithd", "snow", "glpi", "scrapy", "gsuite",
                    # "agentic", "easyvista", "python-dev", "kbot-test",
                )
            ],
            rules=rules,
        ),
        update_mode=UpdaterName.STRICT,
    )
    wa.install()
    wa.update()


if __name__ == "__main__":
    main()
