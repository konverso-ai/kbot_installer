"""Helper module for different Kbot tasks like upgrade, pull, etc."""
# pylint: disable=import-outside-toplevel
# pylint: disable=consider-using-with
# pylint: disable=unspecified-encoding
import os
import os.path
import re
import sys
import gzip
import time

from datetime import datetime

import tarfile
import shutil
import json
import logging
import xml.dom.minidom

import subprocess
from subprocess import TimeoutExpired

DEV_DIR = "/home/konverso/dev/"
WORK_DIR = os.path.join(DEV_DIR, "work")
BIN_DIR = os.path.join(WORK_DIR, "bin")
PYTHON_PATH = os.path.join(BIN_DIR, "python.sh")

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

LOG_FILE = "automatic_kbot_actions.log"
LOG_FILENAME = os.path.join(DEV_DIR, LOG_FILE)


def set_logger(logger, mode, log_filename):
    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s: %(message)s",
                                  datefmt="%Y-%m-%d - %H:%M:%S")
    fh = logging.FileHandler(log_filename, mode)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def get_product_description(product_path):
    """
        Give a product path, returns a dictionnary containing the Product definition
    """
    result = {}
    dom = xml.dom.minidom.parse(product_path)
    for product in dom.getElementsByTagName('product'):

        for attr in ('name', 'version', 'build', 'date', 'type', 'doc'):
            if product.hasAttribute(attr):
                result[attr] = product.getAttribute(attr)

        result["parents"] = []
        for parents in product.getElementsByTagName('parents'):
            for parent in parents.getElementsByTagName('parent'):
                result["parents"].append(parent.getAttribute('name'))

    return result

def test():

    print("TEST")

    from utils import Decrypt

    import Bot
    Bot.Bot().Init()

    from domain.nexus import NexusRepository
    nexus = NexusRepository(Bot.Bot().GetConfig("nexus_host"),
                            Bot.Bot().GetConfig("nexus_user"),
                            Decrypt(Bot.Bot().GetConfig("nexus_password")))

    print("Asking for files from", Bot.Bot().GetConfig("nexus_host"))
    #response = nexus.get_latest_file(f"/{KBOT_FILE_NEXUS_REPOSITORY}/release-2022.03-dev/snow", "/tmp.t")
    nexus_files = nexus.list_repository("kbot_raw")
    print("KBOT files: ", nexus_files)

    print(nexus_files[0].js)

    kbot_file = nexus_files.Filter(folder_name="release-2022.03-dev/jira").latest()
    print("Last kbot file:", kbot_file)


def get_nexus():
    """
        Returns a new instance of the Nexus repository
    """

    if not nexus:
        raise RuntimeError("RuntimeError: Nexus details are unknown. review your parameters")

    return nexus

def install(version, product, create_workarea=False):

    if not os.path.exists(installation_path):
        os.mkdir(installation_path)
    else:
        if not os.path.isdir(installation_path):
            raise RuntimeError(f"Installation path {installation_path} is not a directory !")

    nexus = get_nexus()
    nexus_files = nexus.list_repository("kbot_raw")

    # Load all the required products
    _reccure_product_download(nexus_files, product, version)

    if not create_workarea:
        return

    #
    # Call the installer in non-interactive mode
    #
    cmd = f"{installation_path}/kbot/install.sh "
    cmd += f"--product {product} " # Indicate the top level product for the installation
    cmd += f"--path {installation_path} " # Indicate the installation path
    cmd += "--secret=K0nversOK! " # Secret installation password
    cmd += "--default "
    cmd += "--workarea /home/konverso/work "

    # If hostname is unset, then the user will be prompted for it
    if hostname:
        cmd += f"--hostname {hostname} " # Indicate the best hostname

    if workarea:
        cmd += f"--workarea {workarea} "
    else:
        cmd += "--workarea /home/konverso/dev/work "

    cmd += "--accept-licence "

    response = os.system(cmd)

def _reccure_product_download(nexus_files, product_name, version):
    """
        Recursively retrieve the products, based on the "parent" definition
        found inside the Product definition. 

        Note that:
            if product is Customer or Solution, then do GIT download
            if product is Solution or Framework, then do NEXUS download
    """

    # Check if the product is already installed.
    product_description_path = f"{installation_path}/{product_name}/description.xml"
    import os
    if os.path.exists(product_description_path):
        print(f"Product {product_name} is already installed")
        description = get_product_description(product_description_path)    

        for parent_product_name in description.get("parents"):
            _reccure_product_download(nexus_files, parent_product_name, version)
        return

    print(f"File '{product_description_path}' not found. Installing it")

    # Case of the product not yet installed
    print(f"Product {product_name} is not installed. Retrieving it")

    # Get the most recent file from nexus
    nexus_file = None
    try:
        nexus_files_tmp = nexus_files.Filter(folder_name=f"{version}/{product_name}")
        nexus_file = [x for x in nexus_files_tmp if x.path.endswith("_latest.tar.gz")][0]
    except:
        pass

    if not nexus_file:
        print(f"Product {product_name} is not found in Nexus. Attempting GIT")
        # Not in Nexus, try, to get it from GIT
        import os
        response = os.system(f"git clone https://bitbucket.org/konversoai/{product_name}.git")
        if response:
            raise RuntimeError("Failed clone the git repository")

        # Now set the proper branch
        # REVIEW: Should also check if we are in a Site. If so, we skip the checkout
        if product_name not in ("kkeys",):
            response = os.system(f"cd {installation_path}/{product_name} ; git checkout {version}")
            if response:
                print(f"Failed set git repository to branch {version}. Will stay on master branch")

        os.rename(product_name, f"{installation_path}/{product_name}")

        print(f"Product {product_name} retrieved from GIT")

        # Kick of the reccursion on all required products before exiting.
        parents = get_product_description(f"{installation_path}/{product_name}/description.xml").get("parents")
        for parent in parents:
            _reccure_product_download(nexus_files, parent, version)

        return

    if not nexus_file:
        log.error("Failed to find file %s", f"{version}/{product_name}")
        print("ABORTING")
        return

    _nexus_download_and_install(nexus_file, product_name)

    # Kick of the reccursion on all required products before exiting.
    parents = get_product_description(f"{installation_path}/{product_name}/description.xml").get("parents")
    for parent in parents:
        _reccure_product_download(nexus_files, parent, version)

def _nexus_download_and_install(nexus_file, product_name):
        print(f"    Downloading product {product_name}  using Nexus file: {nexus_file}")
        start = time.time()
        nexus_file.download(f"/tmp/{product_name}.tar.gz")
        seconds = int(time.time() - start)
        print(f"         => completed in {seconds} seconds")

        # Now we can unzip the file
        start = time.time()
        print(f"    Unzipping /tmp/{product_name}.tar.gz")
        try:
            with gzip.open(f"/tmp/{product_name}.tar.gz", 'rb') as f_in:
                with open(f"/tmp/{product_name}.tar", "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        except Exception as e:
            log.error("Failed to extract file %s due to: %e", f"/tmp/{product_name}.tar.gz", e)
            print("ABORTING")
            return
        else:
            seconds = int(time.time() - start)
            print(f"         => completed in {seconds} seconds")

        # Cleanup the downloaded zip file
        os.unlink(f"/tmp/{product_name}.tar.gz")

        if backup == "none":
            os.system(f"rm -rf {installation_path}/{product_name}")
        elif backup == "folder":
            backup_version = 1
            while True:
                backup_folder = f"{installation_path}/{product_name}.backup.{backup_version}"
                if os.path.exists(backup_folder):
                    backup_version += 1
                else:
                    break
            os.rename(f"{installation_path}/{product_name}", backup_folder)

        # And untar the content inside the installer
        start = time.time()
        print(f"    Untarring /tmp/{product_name}.tar")
        with tarfile.open(f"/tmp/{product_name}.tar") as tf:
            tf.extractall(path=installation_path)
        seconds = int(time.time() - start)
        print(f"         => completed in {seconds} seconds")

        # Cleanup the archive tar file
        os.unlink(f"/tmp/{product_name}.tar")

        # Write a STAMP file, as a marker of this activity, and to serve
        # the purpose of time marker for differences
        with open(f"{installation_path}/{product_name}/nexus.json", "w", encoding="utf-8") as fd:
            json.dump(nexus_file.js, fd)

        print(f"    Saved info in {installation_path}/{product_name}/nexus.json")


def update(version='', backup="none", products=None):
    print("Updating")

    products = products or []
    import time

    nexus = get_nexus()
    nexus_files = nexus.list_repository("kbot_raw")

    
    import Bot
    for p in Bot.Bot().products:

        if products and p.name not in products:
            continue

        # IF the product folder contains nexus.json then it means it was installed
        # through nexus. Otherwise it must be a git repository
        local_nexus_descriptor = os.path.join(Bot.Bot().producthome, p.name, "nexus.json")
        if not os.path.exists(local_nexus_descriptor):
            print(f"Product {p.name} is not from Nexus. Ignored")
            continue

        with open(local_nexus_descriptor, encoding="utf-8") as fd:
            local_nexus_descriptor_js = json.load(fd)

        print(f"Checking product: {p.name}")

        # Now build the product version, based on the
        # - the product version (2022.02)
        # - and the optional suffix (dev)
        # to build the release name, such as:
        # - release-2022.02
        # - release-2022.02-dev
        if not version:
            version = f"release-{p.version}"

        # Get the files for this nexus release
        product_nexus_files = nexus_files.Filter(folder_name=f"{version}/{p.name}",
                                                 ends_with=".tar.gz",
                                                 not_ends_with="latest.tar.gz")
        # Get the latest one

        # Handle case of no release file found
        if not product_nexus_files:
            log.error("Failed to find latest file %s", f"{version}/{p.name}/*.tar.gz")
            print("ABORTING")
            return
        nexus_file = product_nexus_files.latest()

        nexus_commit_id = _get_commit_id_from_nexus_path(nexus_file.path)
        install_commit_id = _get_commit_id_from_nexus_path(local_nexus_descriptor_js.get("path"))

        if nexus_commit_id == install_commit_id:
            print(f"Product {p.name} is already on latest available version {nexus_commit_id}")
            continue

        _nexus_download_and_install(nexus_file, p.name)

        print(f"    Saved info in {installation_path}/{p.name}/stamp")

def _get_commit_id_from_nexus_path(nexus_path):
    """ Given a nexus file path or name, returns the commit it, extracted from its name

        For example, with input:
            release-2022.03/gsuite/gsuite_d4ee90638cbffeef00f660e187c2bee8ecaf81b2.tar.gz
        We would get:
            d4ee90638cbffeef00f660e187c2bee8ecaf81b2
    """
    return nexus_path.split("/")[-1].split("_")[-1].split(".")[0]

def list(products=None):
    products = products or []
    import time

    nexus = get_nexus()
    nexus_files = nexus.list_repository("kbot_raw")

    import Bot
    for p in Bot.Bot().products:

        # Check if file is from Nexus
        nexus_source = False
        product_description_path = os.path.join(f"{Bot.Bot().producthome}", p.name, "description.json")
        if os.path.exists(product_description_path):
            nexus_source = True

        print(f"Checking product: {p.name}")

        if nexus_source:

            with open(product_description_path, encoding="utf-8") as fd:
                nexus_js = json.load(fd)

            #print("File: " + str(nexus_js))

            # Now build the product version, based on the
            # - the product version (2022.02)
            # - and the optional suffix (dev)
            # to build the release name, such as:
            # - release-2022.02
            # - release-2022.02-dev
            release = f"release-{nexus_js.get('version')}"

            # Get the files for this nexus release
            product_nexus_files = nexus_files.Filter(folder_name=f"{release}/{p.name}")
            product_nexus_files = product_nexus_files.Filter(ends_with=".tar.gz")
            product_nexus_files = product_nexus_files.Filter(not_ends_with="latest.tar.gz")
            product_nexus_files = product_nexus_files.Filter(not_ends_with="description.json")

            if product_nexus_files:
                js = product_nexus_files.latest().js
                nexus_commit_id = _get_commit_id_from_nexus_path(js.get("path"))
                installed_commit_id = _get_commit_id_from_nexus_path(nexus_js.get("build").get("commit"))
                if nexus_commit_id == installed_commit_id:
                    print(f"    Nexus on latest available code: {js.get('lastModified')} / {nexus_commit_id}")
                else:
                    print(f"    Nexus on OLD VERSION: {nexus_js.get('build').get('timestamp')}/{nexus_js.get('build').get('commit')}")
                    print(f"        Could upgrade to: {js.get('lastModified')} / {nexus_commit_id}")
            else:
                print(f"    Not Nexus")
        else:
            print(f"    Git")

def usage():
    return """
    Nexus user (-n or --nexus)
        In format 'domain:user:password'

    Action (-a or --action). One of:
        upgrade
        install
        update
    """

if __name__ == "__main__":
    import argparse
    emails = []
    email_title = "Kbot actions result"
    # Don't invoke start_kbot() in finalize job
    # (to not spend time)
    nostart = True
    try:
        parser = argparse.ArgumentParser(prog='Kbot_Actions')
        parser.add_argument('-a', '--action', help="upgrade or update", dest='action', required=True)
        parser.add_argument('-v', '--version', help="version such as 2022.03-dev", dest='version', required=False)
        parser.add_argument('-e', '--email', help="Email to send results", action="append", dest='emails', required=False)
        parser.add_argument('-p', '--products', help="List of products to update", action="append", dest='products', required=False)
        parser.add_argument('-b', '--backup', help="Backup strategie", dest='backup', required=False)
        parser.add_argument('-n', '--nexus', help="Details of the nexus account in format host:user:password", dest='nexus', required=False)
        parser.add_argument('-g', '--git', help="Details of the git account in format user:password", dest='git', required=False)
        parser.add_argument('-i', '--installation', help="Installation path, defauls to /home/konverso/dev/installer", dest='installer', required=False)
        parser.add_argument('-w', '--workarea', help="Default work-area path", dest='workarea', required=False)
        parser.add_argument('--hostname', help="Default hostname", dest='hostname', required=False)
        
        # backup, one of:
        # - none (default)
        # - folder: Old folder is saved into .backup.(iterative number)

        result = parser.parse_args()
        action = result.action
        version = result.version
        emails = result.emails or []
        products = result.products or []
        backup = result.backup
        hostname = result.hostname
        workarea = result.workarea
        installation_path = result.installer or "/home/konverso/dev/installer"

        if action == 'test':
            test()
            sys.exit(0)

        #
        # If defined, set the git user / password for this session
        #
        if result.git:
            print("Git password is in command line. This is unsecure. Prefere setting variables GIT_USERNAME and GIT_PASSWORD")
            user, password = result.git.split(":", 1)
            os.environ["GIT_USERNAME"] = user
            os.environ["GIT_PASSWORD"] = password
            project_dir = os.path.dirname(os.path.abspath(__file__))
            os.environ['GIT_ASKPASS'] = os.path.join(project_dir, 'gitpassword.py')

        # Clean log file
        if os.path.exists(LOG_FILENAME):
            os.remove(LOG_FILENAME)
        # Setting up logger
        # If logger is created with "w" mode
        # it's cleaned after Bot.Init
        #set_logger(log, "a", LOG_FILENAME)
        log.info("Kbot actions '%s' started", action)

        #
        # Now get the nexus parameter
        # (Preferably from variables)
        #
        nexus = None
        if result.nexus:
            print("Nexus password is in command line. This is unsecure. Prefere setting variables NEXUS_HOST, NEXUS_USERNAME and NEXUS_PASSWORD")
            host, user, password = result.nexus.split(":", 3)
            from nexus import NexusRepository
            nexus = NexusRepository(host, user, password)
        elif os.environ.get("NEXUS_HOST") and os.environ.get("NEXUS_USERNAME") and os.environ.get("NEXUS_PASSWORD"):
            host, user, password = os.environ["NEXUS_HOST"], os.environ["NEXUS_USERNAME"], os.environ["NEXUS_PASSWORD"]
            nexus = NexusRepository(host, user, password)
        else:
            print(usage())
            print("Nexus repository details are required")
            sys.exit(1)

        # Firstly remove existing cron job for actions
        #remove_cron_job("actions_job")
        if action == "update":
            update(version=version,
                   backup=backup,
                   products=products)

        # Setup the installer folder and a new work-area
        elif action == "install":
            if len(products) != 1:
                print(usage())
                print("Expecting a single product for the case of installation. Found: ", products)
                sys.exit(1)
            install(version=version,
                   product=products[0],
                   create_workarea=True)
            sys.exit(0)

        # Only setup the installer folder
        elif action == "installer-only":
            if len(products) != 1:
                print(usage())
                print("Expecting a single product for the case of installation. Found: ", products)
                sys.exit(1)
            install(version=version,
                   product=products[0],
                   create_workarea=False)
            sys.exit(0)
        elif action == "list":
            list(products=products)
            sys.exit(0)

        
        email_title = "Kbot actions completed"
    except Exception as exp:
        log.error("Exception occurred during Kbot actions:\n%s", str(exp), exc_info=True)
        email_title = "Kbot actions failed"
    #finally:
    #    create_finalize_job(LOG_FILENAME, emails, email_title, nostart)
