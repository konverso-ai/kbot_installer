import os
import json
import xml.dom.minidom

from utils.Logger import logger
log = logger.getPackageLogger('blob')

def get_bucket_provider(provider_name, container_name):
    # Case of Azure:

    if (
        provider_name == "azure_blob"
        and os.environ.get("BUNDLE_AZURE_BLOB_URL")):

        #pylint: disable=import-outside-toplevel
        from utils.bucket_storage.AzureBlob import AzureBlob
        log.debug("Blob URL: %s", os.environ.get("BUNDLE_AZURE_BLOB_URL"))
        return AzureBlob(
            account_url=os.environ.get("BUNDLE_AZURE_BLOB_URL"),
            container_name=container_name)

    # Case of Amazon S3:
    if (
        provider_name =="amazon_s3"
        and os.environ.get("BUNDLE_AMAZON_S3_REGION")
        and os.environ.get("BUNDLE_AMAZON_S3_BUCKET_NAME")):

        #pylint: disable=import-outside-toplevel
        from utils.bucket_storage.AmazonS3 import AmazonS3
        return AmazonS3(
            region_name=os.environ.get("BUNDLE_AMAZON_S3_REGION"),
            bucket_name=os.environ.get("BUNDLE_AMAZON_S3_BUCKET_NAME"),
            cluster_name=container_name)

    if (
        provider_name =="oci_object_storage"
        and os.environ.get("BUNDLE_OCI_BUCKET_NAME")):

        #pylint: disable=import-outside-toplevel
        from utils.bucket_storage.OCIObjectStorage import OCIObjectStorage
        return OCIObjectStorage(
            auth_method=os.environ.get("BUNDLE_OCI_AUTH_METHOD") or "instance_principal",
            bucket_name=os.environ.get("BUNDLE_OCI_BUCKET_NAME"),
            namespace=os.environ.get("BUNDLE_OCI_NAMESPACE"),
            region=os.environ.get("BUNDLE_OCI_REGION") or "eu-paris-1",
            cluster_name=container_name)

    raise RuntimeError("Unsupported storage provider: %s" % provider_name)


def _get_commit_id_from_repository_path(repository_path):
    """Given a repository file path or name, returns the commit it, extracted from its name

    For example, with input:
        release-2022.03/gsuite/gsuite_d4ee90638cbffeef00f660e187c2bee8ecaf81b2.tar.gz
    We would get:
        d4ee90638cbffeef00f660e187c2bee8ecaf81b2
    """
    return repository_path.split("/")[-1].split("_")[-1].split(".")[0]


def _get_json_product_description(installation_path, product_name):
    """Returns a dictionnary containing the product definition, as found in the
    description.json file
    """
    # Check if file is from Nexus
    json_product_description_path = (
        f"{installation_path}/{product_name}/description.json"
    )
    if not os.path.exists(json_product_description_path):
        return None

    with open(json_product_description_path, encoding="utf-8") as fd:
        return json.load(fd)

    return None


def _get_xml_product_description(installation_path, product_name):
    """Returns a dictionnary containing the product definition, as found in the
    description.xml file
    """
    product_description_path = f"{installation_path}/{product_name}/description.xml"
    if not os.path.exists(product_description_path):
        return False

    result = {}
    dom = xml.dom.minidom.parse(product_description_path)
    for product in dom.getElementsByTagName("product"):
        for attr in ("name", "version", "build", "date", "type", "doc"):
            if product.hasAttribute(attr):
                result[attr] = product.getAttribute(attr)

        result["parents"] = []
        for parents in product.getElementsByTagName("parents"):
            for parent in parents.getElementsByTagName("parent"):
                result["parents"].append(parent.getAttribute("name"))

    return result


def _get_latest_available_repository_file(repository_files, product_name, version):
    """Given a list of Repository (file name, timestamp) returns the most recent version of
    the available binaries, onyl considering the "real" files (not returning the latest.tar.gz

     Returns a pair of Timestamp, Filename
    """
    release = version
    if version not in ("dev", "master"):
        release = f"release-{version}"

    # if version in ("dev", "master"):
    #     release = version
    # else:
    #     release = f"release-{version}"

    # Sample file names=
    # release-2026.02/workday/workday_latest.tar.gz

    message = f"No installation file found for version {release} the product {product_name}"

    repository_files = list(repository_files)
    #print("All available product definitions: ", ", ".join([x for (x, y) in repository_files]))
    #print("All available versions: " + ", ".join({x.split("/", 1)[0] for (x, y) in repository_files}))
    if not repository_files:
        raise
        print(message, "(case 1)")
        return None

    product_repository_files = [(x, y) for (x, y) in repository_files if x.startswith(f"{release}/")]
    if not product_repository_files:
        print(message, "(case 2.a. Version missing in repository)")
        print("All available versions: " + ", ".join({x.split("/", 1)[0] for (x, y) in repository_files}))
        return None

    product_repository_files = [(x, y) for (x, y) in repository_files if x.startswith(f"{release}/{product_name}/")]
    if not product_repository_files:
        print(message, "(case 2.b)")
        return None

    product_repository_files = [(x, y) for (x, y) in product_repository_files if not x.startswith(f"{release}/{product_name}/description")]
    if not product_repository_files:
        print(message, "(case 3)")
        return None

    product_repository_files = [(x, y) for (x, y) in product_repository_files if not x.endswith("latest.tar.gz")]
    if not product_repository_files:
        print(message, "(case 4)")
        return None

    product_repository_files = [(x, y) for (x, y) in product_repository_files if not x.endswith("latest.json")]

    product_repository_files = list(product_repository_files)
    product_repository_files.sort(key=lambda x: x[1], reverse=True)

    if not product_repository_files:
        print(message, "(case 5)")
        return None

    return product_repository_files[0]
