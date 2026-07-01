"""Helper module for different Kbot tasks like upgrade, pull, etc."""

# pylint: disable=import-outside-toplevel
# pylint: disable=consider-using-with
# pylint: disable=unspecified-encoding
import json
import os.path
import uuid
import sys
import tarfile
import time
import xml.dom.minidom

from utils.Logger import logger

DEV_DIR = "/home/konverso/dev/"
WORK_DIR = os.path.join(DEV_DIR, "work")
BIN_DIR = os.path.join(WORK_DIR, "bin")
PYTHON_PATH = os.path.join(BIN_DIR, "python.sh")

log = logger.getPackageLogger('report')

LOG_FILE = "automatic_kbot_actions.log"
LOG_FILENAME = os.path.join(DEV_DIR, LOG_FILE)


def get_bucket_provider():
    """
    Returns a new instance of the Nexus repository
    """
    if not bucket_provider:
        _msg = "Nexus details are unknown. review your parameters"
        raise RuntimeError(_msg)
    return bucket_provider

def get_bundle_descriptor(bucket_provider, bundle_name):
    # We retrieve the file
    fname = bundle_name + ".json"
    bundle_descriptor = bucket_provider.get(fname)
    if not bundle_descriptor:
        log.warning("Failed to find file: %s", fname)
        return None

    bundle_json_descriptor = json.loads(bundle_descriptor)
    return bundle_json_descriptor

def install(version, product, create_workarea=False, no_learn=False, recurse=True):
    """Recursive installation of the product and all its related parents,
    for the given version.

    If create_workarea is True, then all runs install.sh
    Arguments:
      version: a bundle name
    """

    if not os.path.exists(installation_path):
        os.mkdir(installation_path)
    else:
        if not os.path.isdir(installation_path):
            msg = f"Installation path {installation_path} is not a directory !"
            raise RuntimeError(msg)

    bucket_repo = get_bucket_provider()
    bundle_json_descriptor = get_bundle_descriptor(bucket_provider=bucket_repo, bundle_name=version)

    if not bundle_json_descriptor:
        print(f"Bundle '{version}' is not currently available. Check name or check it was properly pushed on this bucket")
        sys.exit(1)
    
    # Load all the required products
    recurse_product_download(bundle_json_descriptor, product, version, visited=[], recurse=recurse)

    if not create_workarea:
        return

    admin_password = str(uuid.uuid4())
    #
    # Call the installer in non-interactive mode
    #
    current_folder = os.path.dirname(__file__)
    cmd = f"{current_folder}/setup_workarea.sh "
    # Indicate the top level product for the installation
    cmd += f"--product {product} "
    cmd += f"--path {installation_path} "  # Indicate the installation path
    cmd += f"--secret={admin_password}"  # Secret installation password
    cmd += "--default "
    cmd += "--workarea /home/konverso/work "

    if no_learn:
        cmd += "--no-learn "

    # If hostname is unset, then the user will be prompted for it
    if hostname:
        cmd += f"--hostname {hostname} "  # Indicate the best hostname

    if workarea:
        cmd += f"--workarea {workarea} "
    else:
        cmd += "--workarea /home/konverso/dev/work "

    cmd += "--accept-licence "

    cmd += installation_path

    os.system(cmd)


def _get_json_product_description(product_name):
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


def _get_xml_product_description(product_name):
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


def _get_product_definition(bundle_json_descriptor, product_name):
    """Given a list of NexusFile objects, returns the most recent version of
    the available binaries, onyl considering the "real" files (not returning the latest.tar.gz
    """
    versions = bundle_json_descriptor.get("versions")
    products = [x for x in versions if x.get("name") == product_name]

    if not products: 
        log.debug("Failed to find product '%s' in: %s",
                  product_name, ", ".join(x.get("name") for x in versions))
        return None

    return products[0]

def _xml_products_sorting(xml_product_descriptions):
    """Given a list of xm product definitions (in dict format),
    Sort them on their type, in the following order:
         site, customer, solution, framework
    """
    xml_product_descriptions_new = []
    for t in ("site", "customer", "solution", "framework"):
        descs = [d for d in xml_product_descriptions if d.get("type") == t]
        xml_product_descriptions_new.extend(descs)
    return xml_product_descriptions_new


def _get_tree(xml_descriptions, recurse=True):
    """Ouput if a list of dictionnaries representing the description.xml

         It is basically a FULL version of the description tree, when the parent names
         are replaced by the related description object

         For example:

    {
      "name": "snow",
      ...
      "parents": [
          RELATED PARENT JSON DEFINITION 2,
          RELATED PARENT JSON DEFINITION 1,
      ],
      ...
      "build": {
          "timestamp": "2023/01/25 06:11:05",
          "branch": "release-2022.03",
          "commit": "08f6bc24fe3e181b94c481b4f56a648f4d8d0d01"
      },
      "license": "kbot-included",
      "display": {
          "name": {
              "en": "Kbot for ServiceNow",
              "fr": "Kbot pour ServiceNow"
          },
          "description": {
              "en": "The ServiceNow integration....eady-to-use virtual agent for ServiceNow.",
              "fr": "L'int\u00e9gration \u00e0 ServiceNow. ...emploi pour ServiceNow."
          }
      }
    }
    """
    child_list = []
    visited_product_names = []
    for xml_description in _xml_products_sorting(xml_descriptions):
        if xml_description.get("name") in visited_product_names:
            continue
        xml_description = xml_description.copy()

        if recurse:
            _tree_recurse_visite(
                xml_description, xml_descriptions, visited_product_names
            )
        child_list.append(xml_description)


        if not recurse:
            break

    return child_list


def _tree_recurse_visite(
    xml_description, xml_descriptions, visited_product_names
):
    """Reccursivity helper function of _get_tree"""
    child_list = []
    for parent_name in xml_description.get("parents", []):
        try:
            child_xml_description = [
                x for x in xml_descriptions if x.get("name") == parent_name
            ][0]
        except IndexError:
            print(
                (f"Failed to find referenced product: '{parent_name}' "
                 f"in product '{xml_description.get('name')}'")
            )
            continue

        child_xml_description = child_xml_description.copy()

        _tree_recurse_visite(
            child_xml_description, xml_descriptions, visited_product_names
        )
        child_list.append(child_xml_description)
    xml_description["parents"] = child_list


def tree_print(elements, level=1, visited=None, recurse=True):
    """Print the given list of products, excluding duplication on root level"""

    visited = visited or []
    for element in elements:
        if level == 1 and element.get("name") in visited:
            continue
        visited.append(element.get("name"))

        if recurse:
            print("\t" * level + element.get("name"))
            tree_print(element.get("parents"), level + 1, visited=visited)


def recurse_product_download(bundle_json_descriptor, product_name, version, visited, recurse=True):
    """
    Recursively retrieve the products, based on the "parent" definition
    found inside the Product definition.

    Note that:
        if product is Customer or Solution, then do GIT download
        if product is Solution or Framework, then do NEXUS download

    Arguments: 
        bundle_json_descriptor: A list of product json descriptors (from the bundle)
        version: a bundle name
    """
    if product_name in visited:
        return
    visited.append(product_name)

    print("Checking product:", product_name)
    log.debug("recurse_product_download for product '%s'", product_name)
    #log.warning("Returning get_bundle_descriptor: %s", json.dumps(bundle_json_descriptor, indent=4))

    if not version:
        print("Missing version info. Please add the -v flag")

    # The NEW proposed 
    bundle_product_descriptor = _get_product_definition(bundle_json_descriptor, product_name)

    log.debug("Using product descriptor: %s", json.dumps(bundle_product_descriptor, indent=4))

    # Check if the product is already installed through Nexus
    json_product_description = _get_json_product_description(product_name)

    # For the top level product we will get it as XML
    # If this is git, then may be we do not have a JSON information, and we should
    # get the XML description
    xml_product_description = _get_xml_product_description(product_name)

    #
    # Attempt to figure out the version if not provided
    #
    if not version:
        if json_product_description:
            version = json_product_description.get("version")
        elif xml_product_description:
            version = xml_product_description.get("version")
        else:
            print("Failed to find any version information. Add the -v flag")
            sys.exit(1)
    #
    # Product was installed through Nexus, we see if there is anything to update
    #
    if bundle_product_descriptor:
        download = False
        log.debug("We have a bundle_product_descriptor")
        if json_product_description:
            log.debug("We have a json_product_description")

            # Product already installed. We check if anything new is in the bundle
            installed_commit_id = json_product_description.get("build").get("commit")
            nexus_commit_id = _get_commit_id_from_nexus_path(bundle_product_descriptor.get("build").get("commit"))

            if nexus_commit_id == installed_commit_id:
                print(
                    f"   Product is on latest available version: {bundle_product_descriptor.get('build').get('timestamp')} / {nexus_commit_id}"
                )
            else:
                print(
                    f"    Product on OLD VERSION: {json_product_description.get('build').get('timestamp')}/{json_product_description.get('build').get('commit')}"
                )
                print(
                    f"        Attempting to upgrade to: {bundle_product_descriptor.get('build').get('timestamp')} / {nexus_commit_id}"
                )
                download = True
        else:
            download = True

        if recurse:
            for parent_product_name in bundle_product_descriptor.get("parents"):
                recurse_product_download(bundle_json_descriptor, parent_product_name, version, visited=visited)

        # Product not yet installed. We retrieved its path from the bundle
        if download:
            _bundle_product_download(bundle_product_descriptor, product_name)

        return
    #
    # Product was installed through GIT or some other file copy
    #
    if xml_product_description:
        if not recurse:
            return

        parents = _get_xml_product_description(product_name).get("parents")
        for parent in parents:
            recurse_product_download(bundle_json_descriptor, parent, version, visited=visited)
        return

    #
    # Product was NEVER installed. Install it
    #raise "No product found on %s" % product_name

    # Case of product not existing in repository
    if not json_product_description:
        if not os.path.exists(os.path.join(installation_path, product_name)):
            print(f"Product {product_name} is not found. Attempting GIT")
            # Not in software repository, try, to get it from GIT
            response = os.system(
                f"cd {installation_path} ; git clone https://bitbucket.org/konversoai/{product_name}.git"
            )
            if response:
                print("ERROR: Cannot clone the git repository '%s'. Error code: %s" % (product_name, response))
                return

        if os.path.exists(os.path.join(installation_path, product_name, ".git")):
            # Now set the proper branch
            # REVIEW: Should also check if we are in a Site. If so, we skip the checkout
            response = os.system(
                f"cd {installation_path}/{product_name} ; git checkout release-{version}"
            )
            if response and product_name not in ("kkeys",):
                print(
                    f"Failed set git repository to branch {version}. Will stay on master branch"
                )

            print(f"Product {product_name} retrieved from GIT")

        if not recurse:
            return

        # Kick of the recursion on all required products before exiting.
        parents = _get_xml_product_description(product_name).get("parents")
        for parent in parents:
            recurse_product_download(bundle_json_descriptor, parent, version, visited=visited)

        return

    # We have a good 'latest' nexus file. Use it:
    _bundle_product_download(bundle_product_descriptor, product_name)

    if not recurse:
        return

    for parent in bundle_product_descriptor.get("parents"):
        recurse_product_download(bundle_json_descriptor, parent, version)


def _bundle_product_download(bundle_product_descriptor, product_name):
    """install (replace eventually) the given product using the given bundle definition file

    Returns the description.json dictionnary of the loaded file
    """
    log.debug("_bundle_product_download: %s: %s", product_name, bundle_product_descriptor)
    # Path in Bucket: release-2026.02/workday/workday_9f9b0818e7e51c68f34cb828dadcd0f000ff9259.tar.gz'
    # description: build': {'timestamp': '2026/04/20 07:38:34', 'branch': 'release-2025.02', 'commit': '2ca706c23e038d116bdc5322c9f6c2fdc6bb60b0'}, 'license': 'kbot-included', 'display': {'name': {'en': '', 'fr': ''}, 'description': {'en': '', 'fr': ''}}}
    path = bundle_product_descriptor.get("build").get("branch") + "/"
    path += bundle_product_descriptor.get("name") + "/" 
    path += bundle_product_descriptor.get("name") + "_" + bundle_product_descriptor.get("build").get("commit") + ".tar.gz"

    print(f"    Downloading product {product_name}  using bundle description: {bundle_product_descriptor.get('build').get('timestamp')}")
    start = time.time()
    bucket_artifact_providers.download(path, f"/tmp/{product_name}.tar.gz")
    seconds = int(time.time() - start)
    print(f"         => completed in {seconds} seconds")

    # Untar / Unzip the file
    if not backup or backup == "none":
        os.system(f"rm -rf {installation_path}/{product_name}")
    elif backup == "folder":
        backup_version = 1
        while True:
            backup_folder = (
                f"{installation_path}/{product_name}.backup.{backup_version}"
            )
            if os.path.exists(backup_folder):
                backup_version += 1
            else:
                break
        os.rename(f"{installation_path}/{product_name}", backup_folder)

    # And untar the content inside the installer
    start = time.time()
    print(f"    Untarring /tmp/{product_name}.tar.gz")
    with tarfile.open(f"/tmp/{product_name}.tar.gz", mode="r:*") as tf:
        tf.extractall(path=installation_path)
    seconds = int(time.time() - start)
    print(f"         => completed in {seconds} seconds")

    # Cleanup the archive tar file
    os.unlink(f"/tmp/{product_name}.tar.gz")

    # Write a STAMP file, as a marker of this activity, and to serve
    # the purpose of time marker for differences
    with open(
        f"{installation_path}/{product_name}/nexus.json", "w", encoding="utf-8"
    ) as fd:
        json.dump(bundle_product_descriptor, fd)

    # KB-16459 and KB-14332: Workaround for file magic
    if product_name == "3rdparty":
        fpath = f"{installation_path}/{product_name}/versions.env"

        with open(fpath, "r", encoding="utf-8") as fd:
            content = fd.read()

        content = content.replace(
            "FILE_DIR=${THIRDPARTY_PATH}/file-${FILE_VERSION}",
            "FILE_DIR=/usr/lib/x86_64-linux-gnu",
        )

        with open(fpath, "w", encoding="utf-8") as fd:
            content = fd.write(content)

    print(f"    Saved info in {installation_path}/{product_name}/nexus.json")


def _get_commit_id_from_nexus_path(nexus_path):
    """Given a nexus file path or name, returns the commit it, extracted from its name

    For example, with input:
        release-2022.03/gsuite/gsuite_d4ee90638cbffeef00f660e187c2bee8ecaf81b2.tar.gz
    We would get:
        d4ee90638cbffeef00f660e187c2bee8ecaf81b2
    """
    return nexus_path.split("/")[-1].split("_")[-1].split(".")[0]


def _list_or_update(products=None, update=False, backup=None, target_version=None, recurse=True):
    """List or Update the given products.
    Arguments:
        - target_version: A bundle name
        - products: a List of product names
        - update: a Boolean. If True then attempts to update the products
        - backup: a Boolean. If True will save the product in a .save path before installing new one.
        - recurse: a Boolean. If True, will recurse in the list or updates
    """
    products = products or []

    bundle_json_descriptor = None
    if update and target_version:
        bucket_repo = get_bucket_provider()
        bundle_json_descriptor = get_bundle_descriptor(
            bucket_provider=bucket_repo, bundle_name=target_version
        )

    # First retrieve all the products, and order them
    #
    xml_product_descriptions = []
    for product_name in os.listdir(installation_path):

        if products and not recurse and product_name not in products:
            continue
            
        # print(f"Checking {product_name}")
        xml_product_description = _get_xml_product_description(product_name)
        if not xml_product_description:
            print(
                f"Error: {product_name} is not a valid solution. Missing description.xml"
            )
            continue
        xml_product_descriptions.append(xml_product_description)

    xml_product_descriptions = _xml_products_sorting(xml_product_descriptions)

    # We only print the tree in the List mode
    if not update:
        print("Tree of currently installed products")
        print("====================================")
        top_tree_items = _get_tree(xml_product_descriptions, recurse=recurse)
        tree_print(top_tree_items, recurse=recurse)

    print("Versions of installed products")
    print("==============================")
    # Now check each of the product, to see their version
    for xml_product_description in xml_product_descriptions:
        product_name = xml_product_description.get("name")
        print(f"Checking {xml_product_description.get('type')}: {product_name}")

        # Check if the product is already installed through bucket
        json_product_description = _get_json_product_description(product_name)
        # If this is git, then may be we do not have a JSON information, and we should

        #
        # Attempt to figure out the version if not provided
        #
        if json_product_description:
            # The version (2024.02-dev) is the branch minute the "release-"
            version = json_product_description.get("build").get("branch")[len("release-"):]
            if version:
                print(f"    On product branch '{version}'")

        elif xml_product_description:

            if os.path.exists(f"{installation_path}/{product_name}/.git"):
                # Attempt to find the related GIT branch
                cmd = f"cd {installation_path}/{product_name} ; git status"
                try:
                    cmd_response_text = os.popen(cmd).read()
                    branch = cmd_response_text.split("\n")[0].strip().rsplit(" ", 1)[-1]
                except Exception as e:
                    branch = f"Failed to get GIT version due to {e}"

                print(f"    On GIT branch '{branch}'")

            version = xml_product_description.get("version")
            if version:
                print(f"    Version {version}")
            else:
                print("   (No product version)")
            continue
        else:
            print("    Failed to find any version information")
            continue

        target_version = target_version or version

        if update and version and target_version and target_version != version:
            print(f"    Version is to be updated from {version} to {target_version}")

        # Get the definitions of the latest available version in Bucket
        latest_nexus_definition = None
        if update and bundle_json_descriptor:
            latest_nexus_definition = _get_product_definition(
                bundle_json_descriptor, product_name
            )

        if latest_nexus_definition:
            nexus_commit_id = _get_commit_id_from_nexus_path(
                latest_nexus_definition.js.get("path")
            )
            installed_commit_id = _get_commit_id_from_nexus_path(
                json_product_description.get("build").get("commit")
            )

            if nexus_commit_id == installed_commit_id:
                if update:
                    print(
                        "    Product is already on latest available code: "
                        f"{latest_nexus_definition.js.get('lastModified')} / {nexus_commit_id}"
                    )
                else: # Print
                    branch = latest_nexus_definition.js.get('downloadUrl').split("/")[5]
                    # 'https://nexus.konverso.ai/repository/kbot_raw/release-2025.02/kbot/kbot_399b792296e65da681895427e9c65e69950cbf7a.tar.gz'
                    #  0       2                 3          4        5               6
                    print(
                        f"    Product on branch: {branch}"
                    )

                    print(
                        "    Product on latest available code: "
                        f"{latest_nexus_definition.js.get('lastModified')} / {nexus_commit_id}"
                    )
            else:
                print(
                    "    Product is on OLD VERSION: "
                    f"{json_product_description.get('build').get('timestamp')}/{json_product_description.get('build').get('commit')}"
                )
                if update:
                    _bundle_product_download(
                        latest_nexus_definition, product_name
                    )
                else:
                    print(
                        f"        Could upgrade to: {latest_nexus_definition.js.get('lastModified')} / {nexus_commit_id}"
                    )

        else:
            print("    Version file not found")


def usage():
    return """
    Nexus user (-n or --nexus)
        In format 'domain:user:password'
    Action (-a or --action). One of:
      - upgrade: Update the given installation to a new version. Add variables:
           -v: The target version
      - install: Create a new /installer and /work area, a new bot !
          -w: Define your work area target directory
      - installer-only: Create a new /installer area, without creating a work area
          -v: Version in format
          -p: top product name
      - list: List the installed products.
          No parameters required
    """


if __name__ == "__main__":
    import argparse

    # Don't invoke start_kbot() in finalize job
    # (to not spend time)
    nostart = True
    try:
        parser = argparse.ArgumentParser(prog="Kbot_Actions")
        parser.add_argument(
            "-a",
            "--action",
            help="upgrade or update",
            dest="action",
            default="installer-only"
        )
        parser.add_argument(
            "-b",
            "--bundle",
            help="bundle name",
            dest="bundle",
            required=False,
        )
        parser.add_argument(
            "-e",
            "--email",
            help="Email to send results",
            action="append",
            dest="emails",
            required=False,
        )
        parser.add_argument(
            "-p",
            "--products",
            help="List of products to update",
            action="append",
            dest="products",
            required=False,
        )
        parser.add_argument(
            "--backup", help="Backup strategie", dest="backup", required=False
        )
        parser.add_argument(
            "--bucket",
            help="Details of the Bucket (S3 or AzureBlob) account in format host::region",
            dest="bucket",
            required=False,
        )
        parser.add_argument(
            "-g",
            "--git",
            help="Details of the git account in format user:password",
            dest="git",
            required=False,
        )
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
            "--hostname", help="Default hostname", dest="hostname", required=False
        )
        parser.add_argument(
            "--no-learn",
            help="Do not learn following the setup",
            dest="no_learn",
            action="store_true",
            required=False,
            default=False,
        )
        parser.add_argument(
            "--no-rec",
            help="Do not recurse into product dependencies",
            dest="no_rec",
            action="store_true",
            required=False,
            default=False,
        )
        # backup, one of:
        # - none (default)
        # - folder: Old folder is saved into .backup.(iterative number)

        _result = parser.parse_args()
        action = _result.action.strip()
        bundle_name = _result.bundle
        emails = _result.emails or []
        products = _result.products or []
        backup = _result.backup
        hostname = _result.hostname
        workarea = _result.workarea
        installation_path = _result.installer or "/home/konverso/dev/installer"
        recurse = not _result.no_rec

        #
        # If defined, set the git user / password for this session
        #
        if _result.git:
            print(
                ("Git password is in command line. This is unsecure. "
                 "Prefere setting variables GIT_USERNAME and GIT_PASSWORD")
            )
            user, password = _result.git.split(":", 1)
            os.environ["GIT_USERNAME"] = user
            os.environ["GIT_PASSWORD"] = password
            project_dir = os.path.dirname(os.path.abspath(__file__))
            os.environ["GIT_ASKPASS"] = os.path.join(project_dir, "gitpassword.py")

        # Clean log file
        if os.path.exists(LOG_FILENAME):
            os.remove(LOG_FILENAME)
        # Setting up logger
        # If logger is created with "w" mode
        # it's cleaned after Bot.Init
        log.info("Kbot actions '%s' started", action)

        #
        # Now get the nexus parameter
        # (Preferably from variables)
        #
        bucket = None

        # Case of command line configuration
        if _result.bucket:
            print(
                ("Nexus password is in command line. This is unsecure. "
                 "Prefere setting variables NEXUS_HOST, NEXUS_USERNAME and NEXUS_PASSWORD")
            )

            from utils.bucket_storage.AzureBlob import AzureBlob

            _bucket_type, account_url = _result.bucket.split("::", 1)
            bucket_provider = AzureBlob(account_url=account_url, container_name="bundles")
            bucket_artifact_providers = AzureBlob(account_url=account_url, container_name="artifacts")

        # Case of Azure:
        elif (
            os.environ.get("BUNDLE_PROVIDER") == "azure_blob"
            and os.environ.get("BUNDLE_AZURE_BLOB_URL")):

            from utils.bucket_storage.AzureBlob import AzureBlob
            log.debug("Blob URL: %s", os.environ.get("BUNDLE_AZURE_BLOB_URL"))
            bucket_provider = AzureBlob(
                account_url=os.environ.get("BUNDLE_AZURE_BLOB_URL"),
                container_name="bundles")
            bucket_artifact_providers = AzureBlob(
                account_url=os.environ.get("BUNDLE_AZURE_BLOB_URL"),
                container_name="artifacts")

        # Case of Amazon S3:
        elif (
            os.environ.get("BUNDLE_PROVIDER") == "amazon_s3"
            and os.environ.get("BUNDLE_AMAZON_S3_REGION")
            and os.environ.get("BUNDLE_AMAZON_S3_BUCKET_NAME")):

            from utils.bucket_storage.AmazonS3 import AmazonS3
            bucket_provider =  AmazonS3(
                region_name=os.environ.get("BUNDLE_AMAZON_S3_REGION"),
                bucket_name=os.environ.get("BUNDLE_AMAZON_S3_BUCKET_NAME"),
                cluster_name="bundles")

            bucket_artifact_providers =  AmazonS3(
                region_name=os.environ.get("BUNDLE_AMAZON_S3_REGION"),
                bucket_name=os.environ.get("BUNDLE_AMAZON_S3_BUCKET_NAME"),
                cluster_name="artifacts")
        else:
            print(usage())
            print("Blob Storage repository details are required")
            print("BUNDLE_PROVIDER='%s' and BUNDLE_AZURE_BLOB_URL='%s'" % (
                os.environ.get("BUNDLE_PROVIDER"),
                os.environ.get("BUNDLE_AZURE_BLOB_URL")))
            sys.exit(1)

        # Setup the installer folder and a new work-area
        if action == "install":
            if len(products) != 1:
                print(usage())
                print(
                    "Expecting a single product for the case of installation. Found: ",
                    products,
                )
                sys.exit(1)
            install(
                version=bundle_name,
                product=products[0],
                create_workarea=True,
                no_learn=_result.no_learn,
            )

        # Move to a new version
        elif action == "upgrade":
            _list_or_update(
                backup=backup,
                products=products,
                update=True,
                target_version=bundle_name,
                recurse=recurse
            )

        # Only setup the installer folder
        elif action == "installer-only":
            if not bundle_name:
                print(usage())
                print("A version (-v flag) is mandatory for the action 'installer-only'")
                sys.exit(1)
            if len(products) != 1:
                print(usage())
                print(
                    "Expecting a single product for the case of installation. Found: ",
                    products,
                )
                sys.exit(1)
            install(version=bundle_name, product=products[0], create_workarea=False, recurse=recurse)

        # List the currently installed products
        elif action == "list":
            _list_or_update(products=products, update=False, recurse=recurse)

        else:
            msg = "Invalid action. Should be one of: update, upgrade, install, installer-only"
            print(msg)
            sys.exit(1)

    except Exception as exp:
        log.error("Exception occurred during Kbot actions:\n%s", str(exp), exc_info=True)
        raise SystemExit(99) from exp
