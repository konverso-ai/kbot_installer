"""Helper module for different Kbot tasks like upgrade, pull, etc."""

# pylint: disable=import-outside-toplevel
# pylint: disable=consider-using-with
# pylint: disable=unspecified-encoding
import logging
import os.path
import uuid
import sys
import tarfile
import time

import blob_storage
from blob_storage import (_get_commit_id_from_repository_path,
                          _get_xml_product_description,
                          _get_json_product_description,
                          _get_latest_available_repository_file)

DEV_DIR = "/home/konverso/dev/"
WORK_DIR = os.path.join(DEV_DIR, "work")
BIN_DIR = os.path.join(WORK_DIR, "bin")
PYTHON_PATH = os.path.join(BIN_DIR, "python.sh")

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

LOG_FILE = "automatic_kbot_actions.log"
LOG_FILENAME = os.path.join(DEV_DIR, LOG_FILE)


def set_logger(logger, mode, log_filename):
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d - %H:%M:%S"
    )
    fh = logging.FileHandler(log_filename, mode)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

verbose = False


def install(version, product, create_workarea=False, no_learn=False, recurse=True):
    """Recursive installation of the product and all its related parents,
    for the given version.

    If create_workarea is True, then all runs install.sh
    """
    if verbose:
        print("Installing product '%s' on version '%s'" % (product, version))

    if not os.path.exists(installation_path):
        os.mkdir(installation_path)
    elif not os.path.isdir(installation_path):
        msg = f"Installation path {installation_path} is not a directory !"
        raise RuntimeError(msg)

    bucket_artifact_provider = blob_storage.get_bucket_provider(os.environ.get("BUNDLE_PROVIDER"), "artifacts")
    repository_files = list(bucket_artifact_provider.list_with_last_modified())

    # Load all the required products
    recurse_product_download(repository_files, product, version, recurse=recurse)

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


def recurse_product_download(repository_files, product_name, version, recurse=True):
    """
    Recursively retrieve the products, based on the "parent" definition
    found inside the Product definition.

    Note that:
        if product is Customer or Solution, then do GIT download
        if product is Solution or Framework, then do NEXUS download
    """
    if not repository_files:
        raise RunetimeError(f"Error: Reccurse for file {product_name} cannot continue. No repository files defined")

    if verbose:
        print("Traversing: Checking for product", product_name)

    if not version:
        print("Missing version info. Please add the -v flag")

    # Get the definitions of the latest available version in Release Repository
    file_info = _get_latest_available_repository_file(repository_files, product_name, version)


    if file_info:
        repository_file, ts = file_info
    else:
        repository_file, ts = None, None
        print("Error: Product '%s' is not available in Repository" % product_name)

    # Check if the product is already installed through Release Repository
    json_product_description = _get_json_product_description(installation_path, product_name)
    # If this is git, then may be we do not have a JSON information, and we should
    # get the XML description
    xml_product_description = _get_xml_product_description(installation_path, product_name)

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
    # Product was installed through Release Repository, we see if there is anything to update
    #
    if repository_file and json_product_description:
        installed_commit_id = json_product_description.get("build").get("commit")

        repository_commit_id = _get_commit_id_from_repository_path(repository_file)
        if repository_commit_id == installed_commit_id:
            print(
                f"   Solution is on latest available version: {ts} / {repository_commit_id}"
            )
        else:
            print(
                f"    Solution on OLD VERSION: {json_product_description.get('build').get('timestamp')}/{json_product_description.get('build').get('commit')}"
            )
            print(
                f"        Attempting to upgrade to: {ts} / {repository_commit_id}"
            )
            json_product_description = _repository_download_and_install(
                repository_file, product_name
            )
            if recurse:
                for parent_product_name in json_product_description.get("parents"):
                    recurse_product_download(repository_files, parent_product_name, version)
        return

    #
    # Product was installed through GIT or some other file copy
    #
    if xml_product_description:
        print("   Not installed through Release Repository (probably git ?).")
        if not recurse:
            return

        parents = _get_xml_product_description(installation_path, product_name).get("parents")
        for parent in parents:
            recurse_product_download(repository_files, parent, version)
        return

    #
    # Product was NEVER installed. Install it

    # Case of product not existing in Release Repository
    if not repository_file:
        print(f"Product {product_name} is not found in Release Repository. Attempting GIT")
        # Not in Release Repository, try, to get it from GIT
        response = os.system(
            f"git clone https://bitbucket.org/konversoai/{product_name}.git"
        )
        if response:
            print("ERROR: Cannot clone the git repository '%s'. Error code: %s" % (product_name, response))
            return

        os.rename(product_name, f"{installation_path}/{product_name}")

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
        parents = _get_xml_product_description(installation_path, product_name).get("parents")
        for parent in parents:
            recurse_product_download(repository_files, parent, version)

        return

    # We have a good 'latest' repository file. Use it:
    json_product_description = _repository_download_and_install(repository_file, product_name)

    if not recurse:
        return

    for parent in json_product_description.get("parents"):
        recurse_product_download(repository_files, parent, version)


def _repository_download_and_install(repository_file, product_name):
    """install (replace eventually) the given product using the given repository definition file

    Returns the description.json dictionnary of the loaded file
    """

    print(f"    Downloading product {product_name} using repository file: {repository_file}")
    start = time.time()
    # artifact
    bucket_artifact_provider.download(repository_file, f"/tmp/{product_name}.tar.gz")
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
    repository_json_file = repository_file.replace("tar.gz", "json")
    repository_json_file = repository_json_file.replace(f"/{product_name}_", "/description_")
    print(f"Trying to load {repository_json_file}")
    bucket_artifact_provider.download(repository_json_file, f"{installation_path}/{product_name}/repository.json")

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

    print(f"    Saved info in {installation_path}/{product_name}/repository.json")

    return _get_json_product_description(installation_path, product_name)


def _list_or_update(products=None, update=False, backup=None, target_version=None, recurse=True):
    """List or Update the given products.
    Arguments:
        - products: a List of product names
        - update: a Boolean. If True then attempts to update the products
        - backup: a Boolean. If True will save the product in a .save path before installing new one.
         - recurse: a Boolean. If True, will recurse in the list or updates
    """
    products = products or []

    bucket_artifact_provider = blob_storage.get_bucket_provider(os.environ.get("BUNDLE_PROVIDER"), "artifacts")
    repository_files = list(bucket_artifact_provider.list_with_last_modified())
    #print(list(repository_files))
    #print(version)
    #return

    # First retrieve all the products, and order them
    #
    xml_product_descriptions = []
    for product_name in os.listdir(installation_path):

        if products and not recurse and product_name not in products:
            continue

        if not os.path.isdir(os.path.join(installation_path, product_name)):
            # There may be files, such as bundle.json
            continue

        # print(f"Checking {product_name}")
        xml_product_description = _get_xml_product_description(installation_path, product_name)
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
        # Check if the product is already installed through repository
        json_product_description = _get_json_product_description(installation_path, product_name)
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

        # Get the definitions of the latest available version in repository
        if update:
            # xxxxxxx
            file_info = _get_latest_available_repository_file(
                repository_files, product_name, target_version
            )
        else:
            file_info = _get_latest_available_repository_file(
                repository_files, product_name, version
            )

        if not file_info:
            print("Error: Product '%s' is not available in repository" % product_name)
            sys.exit(1)

        file_name, ts = file_info
        repository_commit_id = _get_commit_id_from_repository_path(file_name)
        installed_commit_id = _get_commit_id_from_repository_path(
            json_product_description.get("build").get("commit")
        )

        if repository_commit_id == installed_commit_id:
            if update:
                print(
                    "    Solution is already on latest available code: "
                    f"{ts} / {repository_commit_id}"
                )
            else: # Print
                branch = file_name.split("/")[-3]
                # 'https://repository.konverso.ai/repository/kbot_raw/release-2025.02/kbot/kbot_399b792296e65da681895427e9c65e69950cbf7a.tar.gz'
                #  0       2                         3          4        5               6
                print(
                    f"    Solution on branch: {branch}"
                )

                print(
                    "    Solution on latest available code: "
                    f"{ts} / {repository_commit_id}"
                )
        else:
            print(
                "    Solution is on OLD VERSION: "
                f"{json_product_description.get('build').get('timestamp')}/{json_product_description.get('build').get('commit')}"
            )
            if update:
                _json_product_description = _repository_download_and_install(
                    file_name, product_name
                )
            else:
                print(
                    f"        Could upgrade to: {ts} / {repository_commit_id}"
                )

def usage():
    return """
    Action (-a or --action). One of:
      - upgrade: Update the given installation to a new version. Add variables:
           -v: The target version
      - install: Create a new /installer and /work area, a new bot !
          -w: Define your work area target directory
      - update: Update the given installation to the latest available code base for this version
          No param required, will simply used the existing product definitions and versions
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
            "-a", "--action",
            help="upgrade or update",
            dest="action",
            required=False,
            default="installer-only"
        )
        parser.add_argument(
            "-v",
            "--version",
            help="version such as 2022.03-dev",
            dest="version",
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
            "-b", "--backup", help="Backup strategie", dest="backup", required=False
        )
        parser.add_argument(
            "-n",
            "--repository",
            help="Details of the repository account in format host:user:password",
            dest="repository",
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
        product_version = (_result.version or "").strip()
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
        # set_logger(log, "a", LOG_FILENAME)
        log.info("Kbot actions '%s' started", action)

        bucket_artifact_provider = blob_storage.get_bucket_provider(os.environ.get("BUNDLE_PROVIDER"), "artifacts")

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
                version=product_version,
                product=products[0],
                create_workarea=True,
                no_learn=_result.no_learn,
            )

        # Update existing version to the latest code base
        elif action == "update":
            _list_or_update(backup=backup, products=products, update=True, recurse=recurse)

        # Move to a new version
        elif action == "upgrade":
            _list_or_update(
                backup=backup,
                products=products,
                update=True,
                target_version=product_version,
                recurse=recurse
            )

        # Only setup the installer folder
        elif action == "installer-only":
            if not product_version:
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
            install(version=product_version, product=products[0], create_workarea=False, recurse=recurse)

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
