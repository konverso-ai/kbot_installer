"""Setup manager for Python documentation."""

from pathlib import Path

from kbot_installer.core.setup.base import BaseSetupManager


class PythonDocsSetupManager(BaseSetupManager):
    """Manager for setting up Python documentation placeholder.

    Creates a placeholder index.html file for Python API documentation
    if the documentation is not available.
    """

    def setup(self) -> None:
        """Set up Python documentation placeholder."""
        kbot_product = self.get_kbot_product()
        pythondocfolder = Path(kbot_product.dirname) / "doc" / "python"
        pythondocfile = pythondocfolder / "index.html"

        if not pythondocfile.exists():
            self.ensure_directory(pythondocfolder)
            with pythondocfile.open("w", encoding="utf8") as fd:
                fd.write(
                    """<title>Bot API documentation</title>
<meta name="description" content="Main Bot module." />
<html>
<body>
<p> Python Docs are only available with the "python-dev" solution installed.</p>
</body>

</html>
"""
                )
