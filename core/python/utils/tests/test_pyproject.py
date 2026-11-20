"""Tests for utils.pyproject module."""

from pathlib import Path

from utils.pyproject import ForceInclude, Project, PyProject, ToolKbot
from utils.utils_for_unit_tests import compare


def test_forceinclude_valid_builds_installer_paths() -> None:
    force_include = ForceInclude.for_project("jira")
    assert compare("eq", force_include.conf, "installer/jira/conf")
    assert compare("eq", force_include.description_xml, "installer/jira/description.xml")
    assert compare("eq", force_include.pyproject_toml, "installer/jira/pyproject.toml")


def test_pyproject_valid_template_serializes_toml() -> None:
    pyproject = PyProject.template(
        project=Project(name="jira", version="2025.01"),
        kbot=ToolKbot(doc=["readme"], categories=["itsm"]),
    )
    toml_content = pyproject.to_toml()
    assert compare("in", 'name = "jira"', toml_content)
    assert compare("in", "[tool.kbot]", toml_content)


def test_pyproject_valid_write_persists_file(tmp_path: Path) -> None:
    pyproject = PyProject.template(
        project=Project(name="jira", version="2025.01"),
        kbot=ToolKbot(doc=["readme"], categories=["itsm"]),
    )
    destination = tmp_path / "pyproject.toml"
    pyproject.write(str(destination))
    assert compare("eq", destination.exists(), True)
    assert compare("in", "jira", destination.read_text(encoding="utf-8"))
