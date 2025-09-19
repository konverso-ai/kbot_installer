"""Helper module for different Kbot tasks like upgrade, pull, etc."""

# pylint: disable=import-outside-toplevel
# pylint: disable=consider-using-with
# pylint: disable=unspecified-encoding
import json
import logging
import os.path
import shutil
import sys
import tarfile
import time
import xml.dom.minidom

from nexus import NexusRepository

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


def get_nexus():
    """
    Returns a new instance of the Nexus repository
    """
    if not nexus:
        msg = "Nexus details are unknown. review your parameters"
        raise RuntimeError(msg)
    return nexus


def install(version, product, create_workarea=False, no_learn=False):
    """Recursive installation of the product and all its related parents,
    for the given version.

    If create_workarea is True, then all runs install.sh
    """

    if not os.path.exists(installation_path):
        os.mkdir(installation_path)
    else:
        if not os.path.isdir(installation_path):
            msg = f"Installation path {installation_path} is not a directory !"
            raise RuntimeError(msg)

    nexus_repo = get_nexus()
    nexus_files = nexus_repo.list_repository("kbot_raw")

    # Load all the required products
    reccurse_product_download(nexus_files, product, version)

    if not create_workarea:
        return

    #
    # Call the installer in non-interactive mode
    #
    current_folder = os.path.dirname(__file__)
    cmd = f"{current_folder}/setup_workarea.sh "
    # Indicate the top level product for the installation
    cmd += f"--product {product} "
    cmd += f"--path {installation_path} "  # Indicate the installation path
    cmd += "--secret=K0nversOK! "  # Secret installation password
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


def _get_latest_available_nexus_file(nexus_files, product_name, version):
    """Given a list of NexusFile objects, returns the most recent version of
    the available binaries, onyl considering the "real" files (not returning the latest.tar.gz
    """
    release = version
    if version not in ("dev", "master"):
        release = f"release-{version}"

    # if version in ("dev", "master"):
    #     release = version
    # else:
    #     release = f"release-{version}"

    product_nexus_files = nexus_files.Filter(folder_name=f"/{release}/{product_name}")
    product_nexus_files = product_nexus_files.Filter(ends_with=".tar.gz")
    product_nexus_files = product_nexus_files.Filter(not_ends_with="latest.tar.gz")
    product_nexus_files = product_nexus_files.Filter(not_ends_with="description.json")

    if product_nexus_files:
        return product_nexus_files.latest()

    return None


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


def _get_tree(xml_descriptions):
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
        _tree_recurse_visite(
            xml_description, xml_descriptions, result, visited_product_names
        )
        child_list.append(xml_description)

    return child_list


def _tree_recurse_visite(
    xml_description, xml_descriptions, result, visited_product_names
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
            child_xml_description, xml_descriptions, result, visited_product_names
        )
        child_list.append(child_xml_description)
    xml_description["parents"] = child_list


def tree_print(elements, level=1, visited=None):
    """Print the given list of products, excluding duplication on root level"""
    visited = visited or []
    for element in elements:
        if level == 1 and element.get("name") in visited:
            continue
        visited.append(element.get("name"))

        print("\t" * level + element.get("name"))
        tree_print(element.get("parents"), level + 1, visited=visited)


def reccurse_product_download(nexus_files, product_name, version):
    """
    Recursively retrieve the products, based on the "parent" definition
    found inside the Product definition.

    Note that:
        if product is Customer or Solution, then do GIT download
        if product is Solution or Framework, then do NEXUS download
    """
    if not version:
        print("Missing version info. Please add the -v flag")

    # Get the definitions of the latest available version in Nexus
    nexus_file = _get_latest_available_nexus_file(nexus_files, product_name, version)

    if not nexus_file:
        product_nexus_files = nexus_files.Filter(contains=f"/{product_name}/")
        print(
            "Error: Failed to find Nexus in product %s for version release-%s. Available versions are: %s"
            % (product_name, version, product_nexus_files)
        )

    # Check if the product is already installed through Nexus
    json_product_description = _get_json_product_description(product_name)
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
    if json_product_description:
        installed_commit_id = json_product_description.get("build").get("commit")
        if not nexus_file:
            print(
                "Error: Failed to find Nexus in product %s for version %s"
                % (product_name, version)
            )

        nexus_commit_id = _get_commit_id_from_nexus_path(nexus_file.js.get("path"))
        if nexus_commit_id == installed_commit_id:
            print(
                f"   Nexus is on latest available version: {nexus_file.js.get('lastModified')} / {nexus_commit_id}"
            )
        else:
            print(
                f"    Nexus on OLD VERSION: {json_product_description.get('build').get('timestamp')}/{json_product_description.get('build').get('commit')}"
            )
            print(
                f"        Attempting to upgrade to: {nexus_file.js.get('lastModified')} / {nexus_commit_id}"
            )
            json_product_description = _nexus_download_and_install(
                nexus_file, product_name
            )
            for parent_product_name in json_product_description.get("parents"):
                reccurse_product_download(nexus_files, parent_product_name, version)
        return

    else:
        # This is a new path... not yet available
        pass

    #
    # Product was installed through GIT or some other file copy
    #
    if xml_product_description:
        print("   Not installed through Nexus (probably git ?).")
        parents = _get_xml_product_description(product_name).get("parents")
        for parent in parents:
            reccurse_product_download(nexus_files, parent, version)
        return

    #
    # Product was NEVER installed. Install it

    # Case of product not existing in Nexus repository
    if not nexus_file:
        print(f"Product {product_name} is not found in Nexus. Attempting GIT")
        # Not in Nexus, try, to get it from GIT
        response = os.system(
            f"git clone https://bitbucket.org/konversoai/{product_name}.git"
        )
        if response:
            raise RuntimeError("Failed clone the git repository")

        os.rename(product_name, f"{installation_path}/{product_name}")

        # Now set the proper branch
        # REVIEW: Should also check if we are in a Site. If so, we skip the checkout
        if product_name not in ("kkeys",):
            response = os.system(
                f"cd {installation_path}/{product_name} ; git checkout release-{version}"
            )
            if response:
                print(
                    f"Failed set git repository to branch {version}. Will stay on master branch"
                )

        print(f"Product {product_name} retrieved from GIT")

        # Kick of the reccursion on all required products before exiting.
        parents = _get_xml_product_description(product_name).get("parents")
        for parent in parents:
            reccurse_product_download(nexus_files, parent, version)

        return

    print(nexus_file)
    # We have a good 'latest' nexus file. Use it:
    json_product_description = _nexus_download_and_install(nexus_file, product_name)
    for parent in json_product_description.get("parents"):
        reccurse_product_download(nexus_files, parent, version)


def _nexus_download_and_install(nexus_file, product_name):
    """install (replace eventually) the given product using the given Nexus definition file

    Returns the description.json dictionnary of the loaded file
    """

    print(f"    Downloading product {product_name}  using Nexus file: {nexus_file}")
    start = time.time()
    nexus_file.download(f"/tmp/{product_name}.tar.gz")
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
        json.dump(nexus_file.js, fd)

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

    return _get_json_product_description(product_name)


def _get_commit_id_from_nexus_path(nexus_path):
    """Given a nexus file path or name, returns the commit it, extracted from its name

    For example, with input:
        release-2022.03/gsuite/gsuite_d4ee90638cbffeef00f660e187c2bee8ecaf81b2.tar.gz
    We would get:
        d4ee90638cbffeef00f660e187c2bee8ecaf81b2
    """
    return nexus_path.split("/")[-1].split("_")[-1].split(".")[0]


def _list_or_update(products=None, update=False, backup=None, target_version=None):
    products = products or []

    nexus = get_nexus()
    nexus_files = nexus.list_repository("kbot_raw")

    # First retrieve all the products, and order them
    xml_product_descriptions = []
    for product_name in os.listdir(installation_path):
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
        top_tree_items = _get_tree(xml_product_descriptions)
        tree_print(top_tree_items)

    print("Versions of installed products")
    print("==============================")
    # Now check each of the product, to see their version
    for xml_product_description in xml_product_descriptions:
        product_name = xml_product_description.get("name")
        print(f"Checking {xml_product_description.get('type')}: {product_name}")
        # Check if the product is already installed through Nexus
        json_product_description = _get_json_product_description(product_name)
        # If this is git, then may be we do not have a JSON information, and we should

        #
        # Attempt to figure out the version if not provided
        #
        if json_product_description:
            version = json_product_description.get("version")
        elif xml_product_description:
            # Attempt to find the related GIT branch
            cmd = f"cd {installation_path}/{product_name} ; git status"
            try:
                cmd_response_text = os.popen(cmd).read()
                branch = cmd_response_text.split("\n")[0].strip().rsplit(" ", 1)[-1]
            except Exception as e:
                branch = f"Failed to get GIT version due to {e}"

            version = xml_product_description.get("version")
            if version:
                print(f"    Git repository, version {version}, branch: {branch}")
            else:
                print(f"    Git repository, no version, branch: {branch}")
            continue
        else:
            print("    Failed to find any version information")
            continue

        target_version = target_version or version

        if update and target_version and target_version != version:
            print(f"    Version is to be updated from {version} to {target_version}")

        # Get the definitions of the latest available version in Nexus
        if update:
            latest_nexus_definition = _get_latest_available_nexus_file(
                nexus_files, product_name, target_version
            )
        else:
            latest_nexus_definition = _get_latest_available_nexus_file(
                nexus_files, product_name, version
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
                        f"    Nexus is already on latest available code: {latest_nexus_definition.js.get('lastModified')} / {nexus_commit_id}"
                    )
                else: # Print
                    branch = latest_nexus_definition.js.get('downloadUrl').split("/")[5]
                    # 'https://nexus.konverso.ai/repository/kbot_raw/release-2025.02/kbot/kbot_399b792296e65da681895427e9c65e69950cbf7a.tar.gz'
                    #  0       2                 3          4        5               6
                    print(
                        f"    Nexus on branch: {branch}"
                    )

                    print(
                        f"    Nexus on latest available code: {latest_nexus_definition.js.get('lastModified')} / {nexus_commit_id}"
                    )
            else:
                print(
                    f"    Nexus is on OLD VERSION: {json_product_description.get('build').get('timestamp')}/{json_product_description.get('build').get('commit')}"
                )
                if update:
                    _json_product_description = _nexus_download_and_install(
                        latest_nexus_definition, product_name
                    )
                else:
                    print(
                        f"        Could upgrade to: {latest_nexus_definition.js.get('lastModified')} / {nexus_commit_id}"
                    )

        else:
            print("    Version file not found in Nexus")


def usage():
    return """
    Nexus user (-n or --nexus)
        In format 'domain:user:password'
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
            "-a", "--action", help="upgrade or update", dest="action", required=True
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
            "--nexus",
            help="Details of the nexus account in format host:user:password",
            dest="nexus",
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

        # backup, one of:
        # - none (default)
        # - folder: Old folder is saved into .backup.(iterative number)

        result = parser.parse_args()
        action = result.action.strip()
        product_version = (result.version or "").strip()
        emails = result.emails or []
        products = result.products or []
        backup = result.backup
        hostname = result.hostname
        workarea = result.workarea
        installation_path = result.installer or "/home/konverso/dev/installer"

        #
        # If defined, set the git user / password for this session
        #
        if result.git:
            print(
                ("Git password is in command line. This is unsecure. "
                 "Prefere setting variables GIT_USERNAME and GIT_PASSWORD")
            )
            user, password = result.git.split(":", 1)
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

        #
        # Now get the nexus parameter
        # (Preferably from variables)
        #
        nexus = None
        if result.nexus:
            print(
                ("Nexus password is in command line. This is unsecure. "
                 "Prefere setting variables NEXUS_HOST, NEXUS_USERNAME and NEXUS_PASSWORD")
            )
            host, user, password = result.nexus.split(":", 3)
            nexus = NexusRepository(host.strip(), user.strip(), password.strip())
        elif (
            os.environ.get("NEXUS_HOST")
            and os.environ.get("NEXUS_USERNAME")
            and os.environ.get("NEXUS_PASSWORD")
        ):
            host, user, password = (
                os.environ["NEXUS_HOST"],
                os.environ["NEXUS_USERNAME"],
                os.environ["NEXUS_PASSWORD"],
            )
            nexus = NexusRepository(host, user, password)
        else:
            print(usage())
            print("Nexus repository details are required")
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
                version=product_version,
                product=products[0],
                create_workarea=True,
                no_learn=result.no_learn,
            )
            sys.exit(0)

        # Update existing version to the latest code base
        elif action == "update":
            _list_or_update(backup=backup, products=products, update=True)
            sys.exit(0)

        # Move to a new version
        elif action == "upgrade":
            _list_or_update(
                backup=backup,
                products=products,
                update=True,
                target_version=product_version,
            )
            sys.exit(0)

        # Only setup the installer folder
        elif action == "installer-only":
            if len(products) != 1:
                print(usage())
                print(
                    "Expecting a single product for the case of installation. Found: ",
                    products,
                )
                sys.exit(1)
            install(version=product_version, product=products[0], create_workarea=False)
            sys.exit(0)

        # List the currently installed products
        elif action == "list":
            _list_or_update(products=products, update=False)
            sys.exit(0)

        else:
            msg = "Invalid action. Should be one of: update, upgrade, install, installer-only"
            print(msg)
            sys.exit(1)

    except Exception as exp:
        log.error("Exception occurred during Kbot actions:\n%s", str(exp), exc_info=True)
        raise SystemExit(99) from exp
