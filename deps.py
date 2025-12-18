import os
import json
import argparse

# FUTURE: WITH GIT HUB and KB
# FIX LATER: 
# 1) from kbot_installer.core import product
# 2) Move this file in the new "product" package (github / Korantin)
from product import Product

def build_dependency_file_rec(product_name, installer_path, products, visit_status=None): 
    visit_status = visit_status or {}
    product_path = os.path.join(installer_path, product_name)
    description_xml_path = os.path.join(product_path, "description.xml")

    product_start =  Product.from_xml_file(description_xml_path)

    json_def = json.loads(product_start.to_json())
    json_def["path"] = product_path
    json_def["description"] = description_xml_path

    graph_object_status = visit_status.get(product_name, "unseen")
    if graph_object_status == "open":
        return False
    elif graph_object_status == "closed":
        return True

    for parent in json_def["parents"]:
        status = build_dependency_file_rec(parent, installer_path, products, visit_status)
        if not status:
            return False

    if product_start.name not in [p.get("name") for p in products]:
        products.append(json_def)

    return json_def


def build_work_area_dependency_file(product_name, installer_path, work_area_path, products=None):
    """Build a dependency file under work/var/products.json"""
    target_folder = os.path.join(work_area_path, "var")
    if not os.path.exists(target_folder):
        os.mkdir(target_folder)

    target_file = os.path.join(target_folder, "products.json")
    if os.path.exists(os.path.join(work_area_path, "var")):
        with open(target_file, "w", encoding="utf-8") as fd:
            fd.write(json.dumps(products, indent=4))

    return build_dependency_file(product_name, installer_path, target_file, products=None)


def build_dependency_file(product_name, installer_path, dependency_file_path, products=None):
    """Build a dependency file under work/var/products.json"""
    products = products or []
    build_dependency_file_rec(product_name, installer_path, products)
    products.reverse()

    with open(dependency_file_path, "w", encoding="utf-8") as fd:
            fd.write(json.dumps(products, indent=4))

def get_dependency(product_name, installer_path, work_area_path):
    products = []
    build_dependency_file_rec(product_name, installer_path, products)
    products.reverse()

    return products

if __name__ == "__main__":
    nostart = True
    parser = argparse.ArgumentParser(prog="Kbot_Actions")
    parser.add_argument(
        "-i",
        "--installation",
        help="Installation path, defauls to /home/konverso/dev/installer",
        dest="installer",
        required=False,
    )

    parser.add_argument(
        "-w",
        "--workarea",
        help="Default work-area path, default to /home/konverso/dev/work",
        dest="workarea",
        required=False,
    )
    parser.add_argument(
        "-p",
        "--product",
        help="First product in the chain",
        action="store",
        dest="product",
        required=False,
    )

    _result = parser.parse_args()
    build_work_area_dependency_file(
        product_name=_result.product,
        installer_path=_result.installer or "/home/konverso/dev/installer",
        dependency_file_path=_result.workarea or "/home/konverso/dev/work",
    )
