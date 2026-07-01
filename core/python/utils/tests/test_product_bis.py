"""Tests for utils.product_bis module."""

import pytest

from utils import product_bis
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "xml_content, expected_name, expected_parents",
    [
        (
            '<product name="jira" version="2025.01" type="solution">'
            '<parents><parent name="ithd"/></parents></product>',
            "jira",
            ["ithd"],
        ),
        (
            '<product name="kbot" version="1.0.0" type="framework"/>',
            "kbot",
            [],
        ),
    ],
)
def test_fromxml_valid_parses_product_metadata(
    xml_content: str,
    expected_name: str,
    expected_parents: list[str],
) -> None:
    product = product_bis.Product.from_xml(xml_content)
    assert compare("eq", product.name, expected_name)
    assert compare("eq", product.parents, expected_parents)


@pytest.mark.parametrize(
    "json_content, expected_name, expected_categories",
    [
        (
            '{"name": "jira", "version": "2025.01", "categories": ["itsm"]}',
            "jira",
            ["itsm"],
        ),
    ],
)
def test_fromjson_valid_parses_product_metadata(
    json_content: str,
    expected_name: str,
    expected_categories: list[str],
) -> None:
    product = product_bis.Product.from_json(json_content)
    assert compare("eq", product.name, expected_name)
    assert compare("eq", product.categories, expected_categories)


@pytest.mark.parametrize(
    "xml_product, json_product, expected",
    [
        (
            product_bis.Product(name="jira", version="1.0.0"),
            product_bis.Product(name="confluence", version="1.0.0"),
            ValueError,
        ),
    ],
)
def test_mergexmljson_invalid_rejects_mismatched_names(
    xml_product: product_bis.Product,
    json_product: product_bis.Product,
    expected: type[BaseException],
) -> None:
    with pytest.raises(expected):
        product_bis.Product.merge_xml_json(xml_product, json_product)
