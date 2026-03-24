"""Tests for utils module."""

from kbot_installer.core.factory.utils import (
    build_class_name,
    build_module_name,
    snake_to_pascal,
)


class TestSnakeToPascal:
    """Test cases for snake_to_pascal function."""

    def test_single_word(self) -> None:
        """Test conversion of single word."""
        assert snake_to_pascal("word") == "Word"

    def test_two_words(self) -> None:
        """Test conversion of two words."""
        assert snake_to_pascal("nexus_provider") == "NexusProvider"

    def test_three_words(self) -> None:
        """Test conversion of three words."""
        assert snake_to_pascal("github_versioner") == "GithubVersioner"

    def test_four_words(self) -> None:
        """Test conversion of four words."""
        assert (
            snake_to_pascal("key_pair_pygit_authentication")
            == "KeyPairPygitAuthentication"
        )

    def test_empty_string(self) -> None:
        """Test conversion of empty string."""
        assert snake_to_pascal("") == ""

    def test_single_underscore(self) -> None:
        """Test conversion of single underscore."""
        assert snake_to_pascal("_") == ""

    def test_multiple_underscores(self) -> None:
        """Test conversion of multiple underscores."""
        assert snake_to_pascal("word__with___underscores") == "WordWithUnderscores"

    def test_leading_underscore(self) -> None:
        """Test conversion of string with leading underscore."""
        assert snake_to_pascal("_private_method") == "PrivateMethod"

    def test_trailing_underscore(self) -> None:
        """Test conversion of string with trailing underscore."""
        assert snake_to_pascal("method_") == "Method"

    def test_mixed_case(self) -> None:
        """Test conversion of mixed case string."""
        assert snake_to_pascal("mixed_Case_String") == "MixedCaseString"


class TestBuildModuleName:
    """Test cases for build_module_name function."""

    def test_simple_package(self) -> None:
        """Test building module name with simple package."""
        assert build_module_name("nexus", "provider") == "nexus_provider"

    def test_nested_package(self) -> None:
        """Test building module name with nested package."""
        assert (
            build_module_name("key_pair", "auth.pygit_authentication")
            == "key_pair_pygit_authentication"
        )

    def test_triple_nested_package(self) -> None:
        """Test building module name with triple nested package."""
        assert build_module_name("test", "a.b.c") == "test_c"

    def test_empty_name(self) -> None:
        """Test building module name with empty name."""
        assert build_module_name("", "provider") == "_provider"

    def test_empty_package(self) -> None:
        """Test building module name with empty package."""
        assert build_module_name("nexus", "") == "nexus_"

    def test_single_character_package(self) -> None:
        """Test building module name with single character package."""
        assert build_module_name("test", "a") == "test_a"

    def test_package_with_underscores(self) -> None:
        """Test building module name with package containing underscores."""
        assert build_module_name("test", "my_package") == "test_my_package"


class TestBuildClassName:
    """Test cases for build_class_name function."""

    def test_simple_package(self) -> None:
        """Test building class name with simple package."""
        assert build_class_name("nexus", "provider") == "NexusProvider"

    def test_nested_package(self) -> None:
        """Test building class name with nested package."""
        assert (
            build_class_name("key_pair", "auth.pygit_authentication")
            == "KeyPairPygitAuthentication"
        )

    def test_triple_nested_package(self) -> None:
        """Test building class name with triple nested package."""
        assert build_class_name("test", "a.b.c") == "TestC"

    def test_empty_name(self) -> None:
        """Test building class name with empty name."""
        assert build_class_name("", "provider") == "Provider"

    def test_empty_package(self) -> None:
        """Test building class name with empty package."""
        assert build_class_name("nexus", "") == "Nexus"

    def test_single_character_package(self) -> None:
        """Test building class name with single character package."""
        assert build_class_name("test", "a") == "TestA"

    def test_package_with_underscores(self) -> None:
        """Test building class name with package containing underscores."""
        assert build_class_name("test", "my_package") == "TestMyPackage"

    def test_uses_snake_to_pascal(self) -> None:
        """Test that build_class_name uses snake_to_pascal internally."""
        # This test verifies that the function calls snake_to_pascal
        # by testing the integration
        result = build_class_name("github", "versioner")
        expected = snake_to_pascal("github_versioner")
        assert result == expected
