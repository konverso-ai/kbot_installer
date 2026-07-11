"""Pydantic models for product pyproject.toml files."""

from __future__ import annotations

from typing_extensions import Self

import tomlkit
from pydantic import BaseModel, ConfigDict, Field, model_validator
from tomlkit.items import Table

from utils.path_utils import ensure_path


class Project(BaseModel):
    """``[project]`` section of a product pyproject.toml."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    version: str
    description: str = "Add your description here"
    readme: str = "README.md"
    authors: list[str] = Field(default_factory=list)
    requires_python: str = Field(
        default=">=3.12, <3.13",
        serialization_alias="requires-python",
    )
    dependencies: list[str] = Field(default_factory=list)


class ForceInclude(BaseModel):
    """``[tool.hatch.build.targets.wheel.force-include]`` section."""

    model_config = ConfigDict(populate_by_name=True)

    conf: str
    description_xml: str = Field(serialization_alias="description.xml")
    pyproject_toml: str = Field(serialization_alias="pyproject.toml")

    @classmethod
    def for_project(cls, name: str) -> ForceInclude:
        """Build force-include paths for a product installer layout.

        Args:
            name: Product name used under ``installer/<name>/``.

        Returns:
            Force-include mapping pointing at installer assets.

        """
        base = f"installer/{name}"
        return cls(
            conf=f"{base}/conf",
            description_xml=f"{base}/description.xml",
            pyproject_toml=f"{base}/pyproject.toml",
        )


class WheelTarget(BaseModel):
    """``[tool.hatch.build.targets.wheel]`` section."""

    model_config = ConfigDict(populate_by_name=True)

    packages: list[str] = Field(default_factory=lambda: ["core/python", "rest"])
    py_modules: list[str] = Field(
        default_factory=lambda: ["Bot", "Load", "Learn", "System"],
        serialization_alias="py-modules",
    )
    sources: dict[str, str] = Field(
        default_factory=lambda: {"core/python": ".", "rest": "."}
    )
    force_include: ForceInclude = Field(serialization_alias="force-include")


class HatchBuildTargets(BaseModel):
    """Hatch wheel build target."""

    wheel: WheelTarget


class HatchBuild(BaseModel):
    """Hatch build configuration."""

    targets: HatchBuildTargets


class Hatch(BaseModel):
    """``[tool.hatch]`` section."""

    build: HatchBuild


class UvIndex(BaseModel):
    """Single ``[[tool.uv.index]]`` entry."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    url: str
    publish_url: str | None = Field(default=None, serialization_alias="publish-url")
    default: bool | None = None


class ToolUv(BaseModel):
    """``[tool.uv]`` section."""

    index: list[UvIndex]


class ToolKbot(BaseModel):
    """``[tool.kbot]`` section."""

    doc: list[str]
    build: str = "__BUILD__"
    date: str = "__DATE__"
    categories: list[str]


class IncludeGroupDependency(BaseModel):
    """Dependency group reference inside ``[dependency-groups]``."""

    model_config = ConfigDict(populate_by_name=True)

    include_group: str = Field(serialization_alias="include-group")


class DependencyGroups(BaseModel):
    """``[dependency-groups]`` section."""

    model_config = ConfigDict(populate_by_name=True)

    lint: list[str] = Field(
        default_factory=lambda: [
            "pylint",
            "pylint-django",
            "pylint-django-settings",
            "pylint-plugin-utils",
            "ruff",
        ]
    )
    typecheck: list[str] = Field(default_factory=lambda: ["ty"])
    test: list[str] = Field(
        default_factory=lambda: [
            "pytest",
            "pytest-cov",
            "pytest-django",
            "testcontainers",
        ]
    )
    dev: list[IncludeGroupDependency] = Field(
        default_factory=lambda: [
            IncludeGroupDependency(include_group="lint"),
            IncludeGroupDependency(include_group="typecheck"),
            IncludeGroupDependency(include_group="test"),
        ]
    )


class BuildSystem(BaseModel):
    """``[build-system]`` section."""

    model_config = ConfigDict(populate_by_name=True)

    requires: list[str] = Field(default_factory=lambda: ["hatchling"])
    build_backend: str = Field(
        default="hatchling.build",
        serialization_alias="build-backend",
    )


class Tool(BaseModel):
    """``[tool]`` section."""

    hatch: Hatch
    uv: ToolUv
    kbot: ToolKbot


class PyProject(BaseModel):
    """Root pyproject.toml document for a product."""

    model_config = ConfigDict(populate_by_name=True)

    project: Project
    build_system: BuildSystem = Field(
        default_factory=BuildSystem,
        serialization_alias="build-system",
    )
    tool: Tool
    dependency_groups: DependencyGroups = Field(
        default_factory=DependencyGroups,
        serialization_alias="dependency-groups",
    )

    @model_validator(mode="after")
    def _derive_force_include(self) -> Self:
        """Ensure force-include paths match the project name."""
        self.tool.hatch.build.targets.wheel.force_include = ForceInclude.for_project(
            self.project.name
        )
        return self

    @classmethod
    def template(
        cls,
        project: Project,
        kbot: ToolKbot,
        *,
        wheel: WheelTarget | None = None,
        dependency_groups: DependencyGroups | None = None,
        uv_indexes: list[UvIndex] | None = None,
    ) -> PyProject:
        """Build a pyproject.toml model from the snow product template.

        Args:
            project: Product metadata for the ``[project]`` section.
            kbot: Kbot metadata for the ``[tool.kbot]`` section.
            wheel: Optional wheel target overrides.
            dependency_groups: Optional dependency group overrides.
            uv_indexes: Optional uv index overrides.

        Returns:
            Validated pyproject.toml model with derived force-include paths.

        """
        wheel_target = wheel or WheelTarget(
            force_include=ForceInclude.for_project(project.name)
        )
        return cls(
            project=project,
            tool=Tool(
                hatch=Hatch(
                    build=HatchBuild(targets=HatchBuildTargets(wheel=wheel_target))
                ),
                uv=ToolUv(index=uv_indexes or _default_uv_indexes()),
                kbot=kbot,
            ),
            dependency_groups=dependency_groups or DependencyGroups(),
        )

    def to_toml(self) -> str:
        """Serialize the model to a TOML string.

        Returns:
            TOML document as a string.

        """
        return tomlkit.dumps(_build_toml_document(self))

    def write(self, file_path: str) -> None:
        """Write the model to a pyproject.toml file.

        Args:
            file_path: Destination TOML file path.

        """
        path = ensure_path(file_path)
        with path.open(mode="w", encoding="utf-8") as file:
            tomlkit.dump(_build_toml_document(self), file)


def _dependency_groups_to_table(groups: DependencyGroups) -> Table:
    """Serialize dependency groups with inline tables for ``dev`` entries."""
    data = groups.model_dump(mode="python", by_alias=True, exclude_none=True)
    table = tomlkit.table()
    for key, value in data.items():
        if key == "dev":
            dev_array = tomlkit.array()
            dev_array.multiline(True)
            for item in value:
                inline = tomlkit.inline_table()
                inline.update(item)
                dev_array.append(inline)
            table[key] = dev_array
        else:
            table[key] = value
    return table


def _build_toml_document(pyproject: PyProject) -> tomlkit.TOMLDocument:
    """Build a tomlkit document from a pyproject model."""
    data = pyproject.model_dump(mode="python", by_alias=True, exclude_none=True)
    doc = tomlkit.document()
    doc.update(
        {key: value for key, value in data.items() if key != "dependency-groups"}
    )
    doc["dependency-groups"] = _dependency_groups_to_table(pyproject.dependency_groups)
    return doc


def _default_uv_indexes() -> list[UvIndex]:
    """Return the default Konverso uv indexes from the snow template."""
    return [
        UvIndex(
            name="konverso-aws-private",
            url=(
                "https://konverso-872515286329.d.codeartifact.eu-west-3.amazonaws.com"
                "/pypi/private-pypi/simple/"
            ),
            publish_url=(
                "https://konverso-872515286329.d.codeartifact.eu-west-3.amazonaws.com"
                "/pypi/private-pypi/"
            ),
        ),
        UvIndex(
            name="konverso-aws-pypi-proxy",
            url=(
                "https://konverso-872515286329.d.codeartifact.eu-west-3.amazonaws.com"
                "/pypi/pypi-proxy/simple/"
            ),
            default=True,
        ),
    ]
