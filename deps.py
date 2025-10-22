import os
import json
import argparse

# FUTURE: WITH GIT HUB and KB
# FIX LATER: from kbot_installer.core import product
from product import Product

def build_dependency_file_rec(product_name, installer_path, products):
    product_path = os.path.join(installer_path, product_name)
    description_xml_path = os.path.join(product_path, "description.xml")

    product_start =  Product.from_xml_file(description_xml_path)

    json_def = json.loads(product_start.to_json())

    # All good, but the "childrens are invalid
    json_def["parents"] = [build_dependency_file_rec(p, installer_path, products)
                           for p in json_def["parents"]]
    json_def["path"] = product_path
    json_def["description"] = description_xml_path

    return json_def

def build_dependency_file(product_name, installer_path, work_area_path, products=None):
    products = products or []
    json_def = build_dependency_file_rec(product_name, installer_path, products)

    target_folder = os.path.join(work_area_path, "var")
    if not os.path.exists(target_folder):
        os.mkdir(target_folder)

    target_file = os.path.join(target_folder, "products.json")
    if os.path.exists(os.path.join(work_area_path, "var")):
        with open(target_file, "w", encoding="utf-8") as fd:
            fd.write(json.dumps(json_def, indent=4))

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
        help="Default work-area path",
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
    build_dependency_file(
        product_name=_result.product,
        installer_path=_result.installer or "/home/konverso/dev/installer",
        work_area_path=_result.workarea or "/home/konverso/dev/work")

