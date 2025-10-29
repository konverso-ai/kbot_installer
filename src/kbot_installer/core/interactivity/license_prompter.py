"""License agreement prompter."""

from pathlib import Path

from kbot_installer.core.interactivity.base import InteractivePrompter


class LicensePrompter:
    """Prompter for license agreement."""

    def __init__(self, *, use_defaults: bool = False, silent: bool = False) -> None:
        """Initialize the prompter.

        Args:
            use_defaults: If True, automatically accept license.
            silent: If True, suppress prompts.

        """
        self.use_defaults = use_defaults
        self.silent = silent

    def prompt_license_agreement(
        self,
        target: str | Path,
        *,
        license_accepted: bool = False,
    ) -> bool:
        """Prompt for license agreement.

        Args:
            target: Target installation directory.
            license_accepted: If True, license is already accepted.

        Returns:
            True if license is accepted.

        """
        prompter = InteractivePrompter(
            use_defaults=self.use_defaults, silent=self.silent
        )

        target_path = Path(target)
        licensekey = target_path / "license.key"

        if not licensekey.exists():
            # Check if license is already accepted
            if license_accepted or self.use_defaults:
                return True

            # Read license from file
            current_file = Path(__file__).resolve()
            license_file = current_file.parent.parent.parent.parent / "LICENSE"

            if not license_file.exists():
                # Try alternative location
                license_file = current_file.parent / "LICENSE"

            if license_file.exists():
                license_text = license_file.read_text(encoding="utf-8")
                print(license_text)

            if prompter.ask_yn("Do you accept the license agreement? [yes]: ", "yes"):
                # Create empty license.key file to mark acceptance
                licensekey.write_text("", encoding="utf-8")
                return True

            return False

        return True
