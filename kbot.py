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

def install(version, product):

    if not os.path.exists("/home/konverso/dev/installer"):
        os.mkdir("/home/konverso/dev/installer")
    else:
        if not os.path.isdir("/home/konverso/dev/installer"):
            raise RuntimeError("Installation path /home/konverso/dev/installer is not a directory !")

    nexus = get_nexus()
    nexus_files = nexus.list_repository("kbot_raw")

    # Load all the required products
    _reccure_product_download(nexus_files, product, version)

def _reccure_product_download(nexus_files, product_name, version):
    """
        Recursively retrieve the products, based on the "parent" definition
        found inside the Product definition. 

        Note that:
            if product is Customer or Solution, then do GIT download
            if product is Solution or Framework, then do NEXUS download
    """

    # Check if the product is already installed.
    product_description_path = f"/home/konverso/dev/installer/{product_name}/description.xml"
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
    try:
        nexus_files = nexus_files.Filter(folder_name=f"{version}/{product_name}")
        nexus_file = nexus_files.latest()
    except:
        nexus_file = None

    if not nexus_file:
        print(f"Product {product_name} is in Nexus. Attempting GIT")
        # Not in Nexus, try, to get it from GIT
        import os
        response = os.system(f"git clone https://konverso@bitbucket.org/konversoai/{product_name}.git")
        if response:
            raise RuntimeError("Failed clone the git repository")

        os.rename(product_name, f"/home/konverso/dev/installer/{product_name}")

        print(f"Product {product_name} retrieved from GIT")

        # Kick of the reccursion on all required products before exiting.
        parents = get_product_description(f"/home/konverso/dev/installer/{product_name}").get("parents")
        for parent in parents:
            _reccure_product_download(nexus_files, parent, version)

        return

    #print(nexus_file.js)
    if not nexus_file:
        log.error("Failed to find file %s", f"{version}/{product_name}")
        print("ABORTING")
        return

    print(f"    Downloading {nexus_file.path}")
    start = time.time()
    nexus_file.download(f"/tmp/{product_name}.tar.gz")
    seconds = int(time.time() - start)
    print(f"         => completed in {seconds} seconds")

    # Kick of the reccursion on all required products before exiting.
    parents = get_product_description(f"/home/konverso/dev/installer/{product_name}").get("parents")
    for parent in parents:
        _reccure_product_download(nexus_files, parent, version)


def _nexus_download_and_install(nexus, nexus_file.path, product_name):
        print(f"    Downloading {nexus_file.path}")
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
            os.system(f"rm -rf /home/konverso/dev/installer/{product_name}")
        elif backup == "folder":
            backup_version = 1
            while True:
                backup_folder = f"/home/konverso/dev/installer/{product_name}.backup.{backup_version}"
                if os.path.exists(backup_folder):
                    backup_version += 1
                else:
                    break
            os.rename(f"/home/konverso/dev/installer/{product_name}", backup_folder)

        # And untar the content inside the installer
        start = time.time()
        print(f"    Untarring /tmp/{product_name}.tar")
        with tarfile.open(f"/tmp/{product_name}.tar") as tf:
            tf.extractall(path="/home/konverso/dev/installer/")
        seconds = int(time.time() - start)
        print(f"         => completed in {seconds} seconds")

        # Cleanup the archive tar file
        os.unlink(f"/tmp/{product_name}.tar")

        # Write a STAMP file, as a marker of this activity, and to serve
        # the purpose of time marker for differences
        with open(f"/home/konverso/dev/installer/{product_name}/stamp", "w", encoding="utf-8") as fd:
            fd.write(f"Source: Nexus: {nexus.host}")
            fd.write(f"\nRepository: /{KBOT_FILE_NEXUS_REPOSITORY}")
            fd.write(f"\nJson: {json.dumps(nexus_file.js, indent=4)}")
            fd.write("\nTimestamp: " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
        print(f"    Saved info in /home/konverso/dev/installer/{p.name}/stamp")



def update(version='', backup="none", products=None):
    print("Updating")

    products = products or []
    import time

    nexus = get_nexus()
    nexus_files = nexus.list_repository("kbot_raw")

    for p in Bot.Bot().products:

        if p.type in ('customer', 'site'):
            continue

        if p.name == "kkeys":
            continue

        if products and p.name not in products:
            continue

        print(f"Checking product: {p.name}")

        # Now build the product version, based on the
        # - the product version (2022.02)
        # - and the optional suffix (dev)
        # to build the release name, such as:
        # - release-2022.02
        # - release-2022.02-dev
        if not version:
            version = f"release-{p.version}"

        # Get the most recent file from nexus
        nexus_file = nexus_files.Filter(folder_name=f"{version}/{p.name}")
        nexus_file = nexus_file.latest()

        #print(nexus_file.js)
        if not nexus_file:
            log.error("Failed to find file %s", f"{version}/{p.name}")
            print("ABORTING")
            return

        print(f"    Downloading {nexus_file.path}")
        start = time.time()
        nexus_file.download(f"/tmp/{p.name}.tar.gz")
        seconds = int(time.time() - start)
        print(f"         => completed in {seconds} seconds")

        # Now we can unzip the file
        start = time.time()
        print(f"    Unzipping /tmp/{p.name}.tar.gz")
        try:
            with gzip.open(f"/tmp/{p.name}.tar.gz", 'rb') as f_in:
                with open(f"/tmp/{p.name}.tar", "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        except Exception as e:
            log.error("Failed to extract file %s due to: %e", f"/tmp/{p.name}.tar.gz", e)
            print("ABORTING")
            return
        else:
            seconds = int(time.time() - start)
            print(f"         => completed in {seconds} seconds")

        # Cleanup the downloaded zip file
        os.unlink(f"/tmp/{p.name}.tar.gz")

        if backup == "none":
            os.system(f"rm -rf /home/konverso/dev/installer/{p.name}")
        elif backup == "folder":
            backup_version = 1
            while True:
                backup_folder = f"/home/konverso/dev/installer/{p.name}.backup.{backup_version}"
                if os.path.exists(backup_folder):
                    backup_version += 1
                else:
                    break
            os.rename(f"/home/konverso/dev/installer/{p.name}", backup_folder)

        # And untar the content inside the installer
        start = time.time()
        print(f"    Untarring /tmp/{p.name}.tar")
        with tarfile.open(f"/tmp/{p.name}.tar") as tf:
            tf.extractall(path="/home/konverso/dev/installer/")
        seconds = int(time.time() - start)
        print(f"         => completed in {seconds} seconds")

        # Cleanup the archive tar file
        os.unlink(f"/tmp/{p.name}.tar")

        # Write a STAMP file, as a marker of this activity, and to serve
        # the purpose of time marker for differences
        with open(f"/home/konverso/dev/installer/{p.name}/stamp", "w", encoding="utf-8") as fd:
            fd.write(f"Source: Nexus: {Bot.Bot().GetConfig('nexus_host')}")
            fd.write(f"\nRepository: /{KBOT_FILE_NEXUS_REPOSITORY}")
            fd.write(f"\nJson: {json.dumps(nexus_file.js, indent=4)}")
            fd.write("\nTimestamp: " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
        print(f"    Saved info in /home/konverso/dev/installer/{p.name}/stamp")

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
        parser.add_argument('-n', '--nexus', help="Details of the nexus account in format user:password", dest='nexus', required=False)

        # backup, one of:
        # - none (default)
        # - folder: Old folder is saved into .backup.(iterative number)

        result = parser.parse_args()
        action = result.action
        version = result.version
        emails = result.emails or []
        products = result.products or []
        backup = result.backup

        if action == 'test':
            test()
            sys.exit(0)

        # Clean log file
        if os.path.exists(LOG_FILENAME):
            os.remove(LOG_FILENAME)
        # Setting up logger
        # If logger is created with "w" mode
        # it's cleaned after Bot.Init
        set_logger(log, "a", LOG_FILENAME)
        log.info("Kbot actions '%s' started", action)

        # Now get the nexus parameter
        nexus = None
        if result.nexus:
            host, user, password = result.nexus.split(":", 3)
            from nexus import NexusRepository
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
        elif action == "install":
            if len(products) != 1:
                print(usage())
                print("Expecting a single product for the case of installation. Found: ", products)
                sys.exit(1)
            install(version=version,
                   product=products[0])
            sys.exit(0)

        email_title = "Kbot actions completed"
    except Exception as exp:
        log.error("Exception occurred during Kbot actions:\n%s", str(exp), exc_info=True)
        email_title = "Kbot actions failed"
    #finally:
    #    create_finalize_job(LOG_FILENAME, emails, email_title, nostart)
