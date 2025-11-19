"""Kbot installer"""

# pylint: disable=too-many-lines

import sys
import os
import shutil
import subprocess
import time
import datetime
import getpass
import socket
import json
import re

import Bot
import classification
from classification import MLObject
from common.Product import ProductList, Product
from common.Config import BotConfig
from common.Errors import KbotLicenseError
from dialog.User import User
import utils
from utils.License import License

import deps
from product import Product as BaseProduct

class Installer:
    """Installer"""

    #pylint: disable=too-many-positional-arguments
    def __init__(self, product=None, path=None, secret=None, default=None, workarea=None, license=None,
                 hostname=None, no_load=False, no_learn=False, no_password=False, db_dump=None):
        """
            product: Optional top level product name. If present, do not ask for the choice of the top level product
            path: Optional path to lookup the products. If defined, do not prompt for the product paths
            secret: Optional default password for the Admin account
            yes: Optional. If true, answers 'yes' to all question asking for a yes/no
            workarea: Optional. Work area location
            default: Optional boolean. If true, then uses the default values
            license: Optional boolean. If true, then considere the license as accepted
            hostname: Optional hostname, typicaly in format site.konverso.ai
        """
        self.path = path or os.path.realpath(os.path.join(os.environ["KBOT_HOME"], ".."))
        self.product = product
        if no_password and not secret:
            self.secret = "lskjf*22SDFSLKsdf"
        else:
            self.secret = secret
        self.default = default
        self.workarea = workarea
        self.license = license
        self.hostname = hostname

        self.products = ProductList()
        self.target = None
        self.config = None
        self.basic_installation = None
        self.update = False
        self.silent = True

        self.installer_log_file = os.path.join('/', 'tmp', 'install.log')

        self.db_dump = db_dump
        self.db_internal = None
        self.db_host = None
        self.db_port = None
        self.db_name = None
        self.db_user = None
        self.db_password = None
        self.pg_ctl = None
        self.pgbouncer_port = None

        self.kbot_external_root_url = None
        self.http_port = None
        self.https_port = None
        self.http_interface = None

        self.redis_internal = None
        self.redis_host = None
        self.redis_port = None
        self.redis_tls_port = None
        self.redis_pwd = None
        self.redis_db_number = None
        self.redis_tls_cert_file = None
        self.redis_tls_key_file = None
        self.redis_tls_ca_cert_file = None
        self.cs_ports_offset = None
        self.admin_password = None

        self.no_load = no_load
        self.no_learn = no_learn

        self.cachedir = None

    def ShowTree(self, product):
        installer = self.path
        work = self.workarea

        # Building the product dependency files.
        products = deps.get_dependency(product, installer, work)
        for prod in products:
            print("{name}\tversion {version}".format(name=prod.get("name"), version=prod.get("version")))

    def Run(self):
        """Run the installer
           Create the work area
        """
        self._StartInstallation()
        self._ReadLicenseAgreement()

        # Build the products
        self._GetProducts()
        self.products.sort_by_type()
        while True:
            work_area = self.workarea or input("Enter work-area location: ").strip()
            self.target = os.path.expanduser(work_area)

            if self.target:
                if os.path.exists(self.target):
                    print(f"ERROR: Directory '{self.target}' already exists!")
                    sys.exit(1)
                break
        if not os.path.exists(self.target):
            os.makedirs(self.target)
        self._SetupProducts()
        self._SetupBin()
        self._SetupCore()
        self._SetupRest()
        self._SetupLogs()
        self._SetupUI()
        self._SetupVar()
        self._SetupCache()
        self._SetupTests()

        self._Link(os.path.join(self.products.kbot().dirname, 'uninstall.sh'), os.path.join(self.target, 'uninstall.sh'))

        self.config = BotConfig(None)
        self.config.Load(products=self.products)
        self._ReadParameters()
        self._SelectInstallationType()
        self._ValidateLicense()
        self._ValidateDatabaseParameters()
        self._ValidatePgBouncer()
        self._ValidateAdminPassword()
        self._ValidateRedisParameters()
        self._ValidateHttpPorts()
        self._ValidateHostname()
        self._UpdatePythonPackages()

        if self.db_internal:
            self._SetupDatabase()
        else:
            self._SetupExternalDatabase()
        self._LoadAndLearn()
        self._FinishInstallation()
        self._SetupPythonDoc()

    def Update(self, silent=False):
        """Update an existing workarea"""
        self.target = os.environ['KBOT_HOME']

        # Load the list of the products

        self.config = BotConfig(None)
        self.config.Load(products=self.products)
        self.https_port = self.config.Get('https_port')
        self.update = True
        self.silent = silent

        self._SetupProducts(update=True)

        self._SetupBin()
        self._SetupCore()
        self._SetupRest()
        self._SetupUI()
        self._SetupTests()
        self._CopyRedisCertificates()
        self._SetupPythonDoc()
        self._UpdatePythonPackages()


    def _SetupPythonDoc(self):
        pythondocfolder = os.path.join(self.products.kbot().dirname, 'doc', 'python')
        pythondocfile = os.path.join(pythondocfolder, "index.html")
        if not os.path.exists(pythondocfile):
            self._Makedirs(pythondocfolder)
            with open(pythondocfile, "w", encoding='utf8') as fd:
                fd.write("""
<title>Bot API documentation</title>
<meta name="description" content="Main Bot module." />
<html>
<body>
<p> Python Docs are only available with the "python-dev" solution installed.</p>
</body>

</html>
""")


    def _SetupBin(self):

        self._LinkProductFilesToDir('bin', os.path.join(self.target, 'bin'))

        # We want the RC script to be a plain file since we are going to recreate it
        rcfilename = os.path.join(self.target, 'bin', 'rc', 'kbot')
        # Remove bin/rc/kbot symlink
        if os.path.exists(rcfilename) or os.path.islink(rcfilename):
            os.unlink(rcfilename)

        # copy kbot file to work area
        #self._Copy(os.path.join(self.products.kbot().dirname, 'bin', 'rc', 'kbot'), rcfilename)
        if os.path.exists(os.path.join(self.products.kbot().dirname, 'bin', 'rc', 'kbot')):
            shutil.copy(os.path.join(self.products.kbot().dirname, 'bin', 'rc', 'kbot'), rcfilename)

        # get current user name
        current_user = getpass.getuser()
        # update rc script with proper path and user name
        #pylint: disable=anomalous-backslash-in-string
        os.system('sed -i "s/__KBOT_HOME__/%s/" %s'%(os.path.abspath(os.path.expanduser(self.target)).replace('/', '\/'), rcfilename))
        os.system('sed -i "s/__KBOT_USER__/%s/" %s'%(current_user, rcfilename))

    def _SetupCore(self):
        dirname = os.path.join(self.target, 'core')
        self._Makedirs(dirname)
        self._LinkProductFilesToDir('core/python', os.path.join(dirname, 'python'), exts=('.py', '.so'))
        for name in ('RunBot', 'Learn', 'Load'):
            for ext in ('', '.py'):
                filename = '%s%s'%(name, ext)
                src = os.path.join(self.products.kbot().dirname, 'core', 'python', filename)
                dst = os.path.join(self.target, 'core', 'python', filename)

                if os.path.exists(dst):
                    os.unlink(dst)
                if os.path.exists(src):
                    
                    self._Copy(src, dst)
                    os.chmod(dst, 0o775)

    def _SetupRest(self):
        for dname in ('api', 'rest_addons'):
            dirname = os.path.join(self.target, 'rest', dname)
            self._Makedirs(dirname)
            self._LinkProductFilesToDir(f'rest/{dname}', dirname, exts=('.py', '.so'))

    def _SetupLogs(self):
        dirname = os.path.join(self.target, 'logs', 'httpd')
        self._Makedirs(dirname)

    def _SetupProducts(self, update=False):
        """Generate a json file with the tree / list of the products

        Args:
            update: Indicate if we are called on an existing (True) or non existing (False) work area
        """
        installer = self.path
        work = self.workarea

        if update and not self.product:
            product_path = os.path.join(work, "var", "products.json")
            with open(product_path, "r", encoding='utf-8') as fd:
                products = json.load(fd)
                self.product = products[0].get("name")

        # Building the product dependency files.
        if self.product:
            deps.build_work_area_dependency_file(self.product, installer, work)

        if update or not len(self.products):
            # at this point we are ready to populate things !
            self.products.populate() #products_definition_file=os.path.join(work, "var", "products.json"))

    def _UpdatePythonPackages(self):
        """ Upate products  python packages using requirements.txt file"""
        for p in self.products:
            if p.type not in ("solution", "customer"):
                continue
            req_path = os.path.join(p.dirname, "requirements.txt")
            if os.path.exists(req_path):
                pip_path = os.path.join(Bot.Bot().binhome, "pip3.sh")
                os.system(f"{pip_path} install -r {req_path} --quiet --disable-pip-version-check")

    def _SetupUI(self):
        dirname = os.path.join(self.target, 'ui')
        self._Makedirs(dirname)
        self._LinkProductFilesToDir('ui', dirname,
                                    ['client', 'locales', 'widget', 'msteams_app', 'msteams_tab', 'in_tab_auth', 'jira_ext', 'chrome_ext'],
                                    ignoredirs=['static'])
        if os.getenv('PYTHON_DIR') and os.getenv("PYTHON_MAJOR_VERSION"):
            self._LinkAbs(os.path.join(os.getenv('PYTHON_DIR'), f'lib/python{os.getenv("PYTHON_MAJOR_VERSION")}/site-packages/drf_yasg/static'),
                          os.path.join(dirname, 'web', 'static'))

    def _SetupVar(self):
        vardir = os.path.join(self.target, 'var')
        dirname = os.path.join(vardir, 'pkl')
        self._Makedirs(dirname)
        self._Makedirs(os.path.join(vardir, 'storage'))
        self._Makedirs(os.path.join(vardir, 'test_results'))
        self._CopyProductFilesToDir('var', vardir)

    def _SetupCache(self):
        self.cachedir = os.path.join(self.target, 'var', 'cache')
        self._Makedirs(self.cachedir)

    def _SetupTests(self):
        dirname = os.path.join(self.target, 'tests')
        if os.path.exists(os.path.join(self.products.kbot().dirname, 'tests')):
            self._Makedirs(dirname)
            self._LinkProductFilesToDir('tests', dirname)
        elif self.update and os.path.exists(dirname):
            if self.silent or self._AskYN("Not used directory 'tests' (%s). Remove it? [yes]" % dirname):
                shutil.rmtree(dirname)

    def _PortInUse(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        res = sock.connect_ex(('127.0.0.1', int(port)))
        sock.close()
        if res == 0:
            return True
        return False

    def _ReadParameters(self):
        """Read some parameters from kbot.conf"""
        # DB
        if self.db_internal is None:
            val = self.config.Get('db_internal')
            self.db_internal = bool(val is None or val == 'true')

        self.db_host = self.db_host or self.config.Get('db_host') or 'localhost'
        self.db_port = self.db_port or self.config.Get('db_port') or '5432'
        self.db_name = self.db_name or self.config.Get('db_name') or 'kbot_db'
        self.db_user = self.db_user or self.config.Get('db_user') or 'kbot_db_user'
        self.db_password = self.db_password or utils.Decrypt(self.config.Get('db_password')) or 'kbot_db_pwd'

        self.pgbouncer_port = self.config.Get('pgbouncer_port') or '6432'
        # Apache
        self.http_interface = self.config.Get('http_interface') or '*'
        self.http_port = self.config.Get('http_port')
        self.https_port = self.config.Get('https_port')

        redis_val = self.config.Get('redis_internal')
        self.redis_internal = bool(redis_val is None or redis_val == 'true')
        self.redis_host = self.config.Get('redis_host')
        self.redis_port = self.config.Get('redis_port')
        self.redis_tls_port = self.config.Get('redis_tls_port')
        self.redis_db_number = self.config.Get('redis_db_number')
        self.redis_pwd = self.config.Get('redis_pwd')
        self.redis_tls_cert_file = self.config.Get('redis_tls_cert_file')
        self.redis_tls_key_file = self.config.Get('redis_tls_key_file')
        self.redis_tls_ca_cert_file = self.config.Get('redis_tls_ca_cert_file')

    def _ValidateDatabaseParameters(self):
        """Ask and validate database parameters"""

        if not self.basic_installation:
            # Advanced installation
            db_internal_str = "yes" if self.db_internal else "no"
            self.db_internal = self._AskYN("Install own Kbot database engine? [%s]: "%db_internal_str, db_internal_str)

            while True:
                # hostname for external database
                if not self.db_internal:
                    self.db_host = input("Enter a hostname where external database is located [%s]: "%self.db_host).strip() or self.db_host

                # database port
                while True:
                    self.db_port = self._AskPort("Specify the database port number", self.db_port, 'db', self.db_internal)
                    if self.db_internal:
                        # check if DB port is in use
                        if self._PortInUse(self.db_port):
                            print("Port %s already in use now, please specify another port."%self.db_port)
                        else:
                            break
                    else:
                        break

                self.db_name = input("Enter a database name [%s]: "%self.db_name).strip() or self.db_name
                self.db_user = input("Enter a database user name [%s]: "%self.db_user).strip() or self.db_user
                self.db_password = input("Enter a password for database user [%s]: "%self.db_password).strip() or self.db_password

                if not self.db_internal:
                    pg_psql = os.path.join(os.environ['PG_DIR'], 'bin', 'psql')
                    if os.system("export PGPASSWORD='%s';%s -h %s -p %s -d %s -U %s -c 'select 1' > /dev/null"\
                            %(self.db_password, pg_psql, self.db_host, self.db_port, self.db_name, self.db_user)) == 0:
                        break
                    print("Can't connect to an external database with specified parameters!")
                else:
                    break

    def _ValidatePgBouncer(self):
        """Ask and validate pgbouncer parameters"""

        if not self.basic_installation:
            # Advanced installation
            use_pgbouncer = self._AskYN("Use pgbouncer? [no]: ", "no")
            if use_pgbouncer:
                self._SaveVariable("use_pgbouncer", "true")
                self.pgbouncer_port = self._AskPort("Specify the pgbouncer port number", self.pgbouncer_port, 'db')
                self._SaveVariable("pgbouncer_port", str(self.pgbouncer_port))

                targetdir = os.path.join(self.target, 'conf')
                sourcedir = os.path.join(self.target, 'products', 'kbot', 'conf')
                for fname in ('pgbouncer.ini', 'userlist.txt'):
                    tfile = os.path.join(targetdir, fname)
                    sfile = os.path.join(sourcedir, fname)
                    self._Copy(sfile, tfile)
                    # pylint: disable=anomalous-backslash-in-string
                    os.system('sed -i "s/__KBOT_HOME__/%s/" %s'%(os.path.abspath(os.path.expanduser(self.target)).replace('/', '\/'), tfile))
                    os.system('sed -i "s/__DB_HOST__/%s/" %s'%(self.db_host, tfile))
                    os.system('sed -i "s/__DB_NAME__/%s/" %s'%(self.db_name, tfile))
                    os.system('sed -i "s/__DB_NAME__/%s/" %s'%(self.db_name, tfile))
                    os.system('sed -i "s/__DB_PORT__/%s/" %s'%(self.db_port, tfile))
                    os.system('sed -i "s/__DB_USER__/%s/" %s'%(self.db_user, tfile))
                    os.system('sed -i "s/__DB_PASSWORD__/%s/" %s'%(self.db_password, tfile))
                    os.system('sed -i "s/__PGBOUNCER_PORT__/%s/" %s'%(self.pgbouncer_port, tfile))

    def _ValidateRedisParameters(self):
        """Ask and validate redis parameters"""
        if self.basic_installation:
            self._Makedirs(os.path.join(self.cachedir, 'redis'))
        else:
            # Advanced installation
            redis_internal_str = "yes" if self.redis_internal else "no"
            self.redis_internal = self._AskYN("Install own Kbot Redis engine? [%s]: " %redis_internal_str,
                                           redis_internal_str)
            if self.redis_internal:
                self._Makedirs(os.path.join(self.cachedir, 'redis'))
            # hostname for external database
            else:
                self.redis_host = input("Enter a hostname where external Redis is located [%s]: "%self.redis_host).strip() or self.redis_host
                # Redis database number
                self.redis_db_number = input(
                    "Enter a database number [%s]: " %self.redis_db_number).strip() or self.redis_db_number
                # Redis default user password
                redis_auth = 'yes' if self.redis_pwd else 'no'
                redis_secured = self._AskYN("Is your redis db is secured with a password? [%s]: " %redis_auth, redis_auth)
                if redis_secured:
                    self._ValidateRedisPassword()
                    # Redis TLS
                    redis_tls = 'yes' if self.redis_tls_port else 'no'
                    if self._AskYN("Use redis db with TLS? [%s]: " %redis_tls, redis_tls):
                        while True:
                            self.redis_tls_port = self._AskPort("Specify the Redis port number",
                                                                self.redis_port, 'redis')
                            # check if DB port is in use
                            if self._PortInUse(self.redis_tls_port):
                                print("Port %s already in use now, please specify another port." % self.redis_tls_port)
                            else:
                                self.redis_port = 0
                                break
                        redis_tls_files = 'no' if self.redis_tls_cert_file and self.redis_tls_key_file and self.redis_tls_ca_cert_file  else 'yes'
                        if self._AskYN("Genetrate redis SSL files? [%s]: " %redis_tls_files, redis_tls_files):
                            self._CopyRedisCertificates()
                        else:

                            question = "Enter full path to redis certificate file [%s]: "
                            question = (question % self.redis_tls_cert_file).strip()
                            self.redis_tls_cert_file = input(question) or self.redis_tls_cert_file

                            question = "Enter full path to redis key file [%s]: "
                            question = (question % self.redis_tls_key_file).strip()
                            self.redis_tls_key_file = input(question) or self.redis_tls_key_file

                            question = "Enter full path to redis Certificate Authority file [%s]: "
                            question = (question % self.redis_tls_ca_cert_file).strip()
                            self.redis_tls_ca_cert_file = input(question) or self.redis_tls_ca_cert_file


    def _ValidateParameterInKbotConf(self, param, param_name):
        if not self.config.Get(param):
            print("Can't find %s (%s) in kbot.conf" % (param, param_name))
            sys.exit(1)

    def _ValidateAdminPassword(self):
        while True:
            prompt = "Enter a password for the default 'admin' user: "
            if self.secret:
                password = self.secret
            elif sys.stdin.isatty():
                password = getpass.getpass(prompt)
            else:
                print(prompt)
                password = sys.stdin.readline().rstrip()
            if password:
                # check if password is strong
                if not User.IsStrongPassword(password):
                    print("This password is not strong enough")
                else:
                    # confirm password
                    prompt = "Confirm password for the default 'admin' user: "
                    if self.secret:
                        confirm_password = self.secret
                    elif sys.stdin.isatty():
                        confirm_password = getpass.getpass(prompt)
                    else:
                        print(prompt)
                        confirm_password = sys.stdin.readline().rstrip()

                    if password != confirm_password:
                        print("Passwords are not the same")
                        sys.stdout.flush()
                    else:
                        self.admin_password = utils.SafeEncrypt(password)
                        break

    def _ValidateRedisPassword(self):
        while True:
            prompt = "Enter password for the default 'Redis' user: "
            if sys.stdin.isatty():
                password = getpass.getpass(prompt)
            else:
                password = sys.stdin.readline().rstrip()
            if password:
                # confirm password
                # prompt = "Confirm password for the default 'Redis' user: "
                if sys.stdin.isatty():
                    confirm_password = getpass.getpass(prompt)
                else:
                    confirm_password = sys.stdin.readline().rstrip()
                if password != confirm_password:
                    print("Passwords are not the same")
                    sys.stdout.flush()
                else:
                    self.redis_pwd = password
                    break

    def _ValidateLicense(self):
        
        licensekey = self.products.get_conf_file('license.key')

        if not licensekey:
            print("ERROR: Missing license file. Add it in one of your product to path conf/license.key")
            sys.exit(1)

        setup_license = True
        if os.path.exists(licensekey):
            try:
                License(licensekey).Validate()
                self._Link(licensekey, os.path.join(self.target, 'var', 'license.key'))
                setup_license = False
            except KbotLicenseError as e:
                print("ERROR: Invalid license file", licensekey)
                sys.exit(1)

    def _ReadLicenseAgreement(self):
        if self.license:
            print("User license agreement is accepted based on command parameters.")
            return
        while True:
            answer = input("Read the user license agreement (r), accept (a) or reject and exit (q): ").strip().lower()
            if answer == 'r':
                os.system("less %s" % os.path.join(os.path.dirname(os.path.abspath(__file__)), 'license.txt'))
            elif answer == 'a':
                print("User license agreement is accepted.")
                break
            elif answer == 'q':
                print("User license agreement is not accepted, exiting...")
                sys.exit(1)

    def _ValidateHostname(self):
        hostname = self.config.Get('hostname')
        kbot_external_root_url = self.config.Get('kbot_external_root_url')
        default_hostname = socket.gethostname() + ".konverso.ai"

        while True:
            if self.hostname:
                answer = self.hostname
            elif hostname and hostname.strip():
                answer = hostname.strip()
            else:
                # Make a default proposal:
                default_hostname = socket.gethostname() + ".konverso.ai"
                answer = input(f"Specify the current host name [{default_hostname}]: ").strip()

            if answer:
                self.hostname = answer
                break

            if not answer and hostname:
                self.hostname = hostname
                break

            self.hostname = default_hostname

        while True:
            if not kbot_external_root_url or kbot_external_root_url == 'https://server.domain.com':
                if self.https_port:
                    kbot_external_root_url = "https://%s"%self.hostname
                else:
                    kbot_external_root_url = "http://%s"%self.hostname

            if self.default:
                answer = kbot_external_root_url
            else:
                answer = input("Specify the external URL of UI [%s]: "%kbot_external_root_url).strip()

            if not answer and kbot_external_root_url:
                self.kbot_external_root_url = kbot_external_root_url
                break

            if answer:
                self.kbot_external_root_url = answer
                break

    def _ValidateHttpPorts(self):
        if not self.basic_installation:
            print("By default web server accepts connections from any ('*') network interfaces.")
            print('If you have a proxy web server behind Kbot web server you would need to accept only local connections.')
            print("In this case specify 'localhost' interface")
            self.http_interface = input("Specify the network interface which web server should listen on [%s]: "\
                                        %self.http_interface).strip() or self.http_interface

            has_http = 'yes' if self.http_port else 'no'
            if self._AskYN("Are you going to use HTTP port? [%s]: " % has_http, has_http):
                self.http_port = self._AskPort("Enter HTTP port number for web server in range 1024..65535", self.http_port, 'http')
            else:
                self.http_port = None

            has_https = 'yes' if self.https_port else 'no'
            if self.http_port is None or self._AskYN("Are you going to use HTTPS port for secure connections? [%s]: " % has_https, has_https):
                self.https_port = self._AskPort("Enter HTTPS port number for web server in range 1024..65535", self.https_port, 'https')
            else:
                self.https_port = None

    def _CopyRedisCertificates(self):
        # if Redis tls is enabled then generate self-signed certificate
        if self.redis_tls_port:
            for name in ('redis.crt', 'redis.key', 'ca.crt'):
                for filename in self.products.get_files('conf/certificates', name):
                    dst = os.path.join(self.target, 'conf', 'certificates', name)
                    if self.update and os.path.exists(dst) and os.path.getmtime(filename) > os.path.getmtime(dst):
                        if self.silent or self._AskYN("Newer file '%s'. Update in workarea? [yes] " % (filename)):
                            os.unlink(dst)
                            self._Copy(filename, dst)
                    break
                else:
                    if not self.update:
                        print("Didn't find '%s' certificate. Will generate certificates.\n" % (name))
                        sys.stdout.flush()
                        os.system(os.path.join(self.target, 'bin', 'gen_redis_certs.sh'))
                        self._UpdateRedisCertificatesPaths()
                        break

    def _UpdateRedisCertificatesPaths(self):
        self.redis_tls_cert_file = os.path.join(self.target, 'conf', 'certificates', 'redis.crt')
        self.redis_tls_key_file = os.path.join(self.target, 'conf', 'certificates', 'redis.key')
        self.redis_tls_ca_cert_file = os.path.join(self.target, 'conf', 'certificates', 'ca.crt')

    def _SaveVariable(self, name, value):
        """Save the variable in configuration file
        If it is already exists then update its value
        If not exists then add
        """
        print("We recommend you add the following to your site kbot.conf")
        print(f"{name} = {value}")
        return

        kbotconf = os.path.join(self.target, 'conf', 'kbot.conf')
        products_value = self.config.GetProducts(name)
        saved_value = self.config.Get(name)
        value = str(value or '')
        if name.endswith('_password'):
            products_value = utils.Decrypt(products_value)
            saved_value = utils.Decrypt(saved_value)
            raw_value = utils.Decrypt(value)
        else:
            raw_value = value
        if (products_value is None or products_value != raw_value) and saved_value != raw_value:
            # verify we don't have commented out variable
            commented = False
            present = False
            if os.path.exists(kbotconf):
                with open(kbotconf, 'r', encoding='utf8') as fd:
                    for line in fd:
                        if re.match(r"#%s\s*="%name, line):
                            commented = True
                            break

                        if re.match(r"%s\s*="%name, line):
                            present = True
                            break
            #pylint: disable=anomalous-backslash-in-string
            if commented:
                os.system('sed -i "s/^#%s\s=.*/%s = %s/" %s'%(name, name, str(value).replace('/', '\/'), kbotconf))
            elif present:
                os.system('sed -i "s/^%s\s=.*/%s = %s/" %s'%(name, name, str(value).replace('/', '\/'), kbotconf))
            else:
                add_new_line = False
                with open(kbotconf, 'r', encoding='utf8') as fd:
                    lines = fd.read()
                    if lines and lines[-1] != '\n':
                        add_new_line = True
                with open(kbotconf, 'a+', encoding='utf8') as fd:
                    if add_new_line:
                        fd.write('\n')
                    fd.write("%s = %s\n" % (name, value))

    def _SetupExternalDatabase(self):
        pg_dir = os.environ['PG_DIR']
        pg_bin = os.path.join(pg_dir, 'bin')
        pg_psql = os.path.join(pg_bin, 'psql')

        # load database schema definition
        print("Loading tables to external database...")
        sys.stdout.flush()
        for product in reversed(self.products):
            sqlfile = os.path.join(self.path, product.name, 'db', 'init', 'db_schema.sql')
            if os.path.exists(sqlfile):
                if os.system("export PGPASSWORD='%s';%s -q -h %s -p %s -d %s -U %s -f %s"\
                             %(self.db_password, pg_psql, self.db_host, self.db_port, self.db_name, self.db_user, sqlfile)) != 0:
                    print("Error: can't load tables! Aborting...")
                    sys.exit(1)

    def _SetupDatabase(self):

        pg_dir = os.environ['PG_DIR']
        pg_bin = os.path.join(pg_dir, 'bin')
        pg_psql = os.path.join(pg_bin, 'psql')
        pg_ctl = os.path.join(pg_bin, 'pg_ctl')
        self.pg_ctl = pg_ctl
        pg_data = os.path.join(self.target, 'var', 'db')


        if not os.path.exists(os.path.join(pg_data, 'PG_VERSION')):
            print("\nInstalling PostgreSQL server...")
            sys.stdout.flush()
            try:
                result = self._CommandOutput([pg_ctl, '-D', pg_data, '-o', '"-E UTF8"', '-o', '"--locale=en_US.utf8"', 'initdb'])
            except subprocess.CalledProcessError:
                print("Cannot init database! Aborting...")
                sys.exit(1)

        try:
            result = self._CommandOutput([pg_ctl, 'status', '--silent', '-D', pg_data])
        except subprocess.CalledProcessError:
            # DB is not up, try to start it
            print("Starting PostgreSQL server...")
            sys.stdout.flush()
            os.system("%s start -l %s/logs/postgres.log -D %s --silent -w -o '-p %s'" % (pg_ctl, self.target, pg_data, self.db_port))

        #pg_status = os.system('%s status --silent -D %s' % (pg_ctl, pg_data))
        try:
            result = self._CommandOutput([pg_ctl, 'status', '--silent', '-D', pg_data])
        except subprocess.CalledProcessError:
            #if pg_status != 0:
            print(result)
            print("Error: can't start PostgreSQL server! Aborting...")
            sys.exit(1)

        # create PostgreSQL user if not exists
        pg_user_exists = self._CommandOutput([pg_psql, 'postgres', '-t', '-A', '-p', self.db_port,
                                              '-c', "SELECT count(*) FROM pg_user WHERE usename = '%s'"%self.db_user])
        if pg_user_exists == "0":
            print("Creating PostgreSQL user %s..." % self.db_user)
            sys.stdout.flush()
            os.system('%s postgres -q -p %s -c "CREATE USER %s PASSWORD \'%s\'"'%(pg_psql, self.db_port, self.db_user, self.db_password))
        else:
            print("PostgreSQL user %s already exists."%self.db_user)

        # create PostgreSQL database if not exists
        pg_db_exists = self._CommandOutput([pg_psql, 'postgres', '-t', '-A', '-p', self.db_port,
                                            '-c', "SELECT count(*) FROM pg_database WHERE datname = '%s'" % self.db_name])
        if pg_db_exists == "0":
            print("Creating PostgreSQL database %s..." % self.db_name)
            sys.stdout.flush()
            os.system('%s postgres -q -p %s -c "CREATE DATABASE %s ENCODING \'UTF8\' OWNER %s"'%(pg_psql, self.db_port, self.db_name, self.db_user))
            os.system('%s -q -p %s %s -c "ALTER SCHEMA public OWNER TO %s"'%(pg_psql, self.db_port, self.db_name, self.db_user))
            os.system('%s -q -p %s %s -c "ALTER SYSTEM SET max_connections TO \'512\'"'%(pg_psql, self.db_port, self.db_name))
        else:
            print("PostgreSQL database %s already exists." % self.db_name)

        sys.stdout.flush()

        if self.db_dump:
            self._InitializeDatabaseFromDump()
        else:
            self._InitializeDatabaseFromScratch()

    def _InitializeDatabaseFromDump(self):
        print("=> Will initialize database from a dump")
        pg_dir = os.environ['PG_DIR']
        pg_bin = os.path.join(pg_dir, 'bin')
        pg_psql = os.path.join(pg_bin, 'psql')

        cmd = '%s -v ON_ERROR_STOP=1 %s -U %s -h %s -p %s -q -c "DROP OWNED BY %s"'
        cmd = cmd % (pg_psql, self.db_name, "konverso", "localhost", self.db_port, self.db_user)
        os.system(cmd)

        cmd = '%s -v ON_ERROR_STOP=1 %s -U %s -h %s -p %s -q -f %s  > /dev/null'
        cmd = cmd % (pg_psql, self.db_name, self.db_user, "localhost", self.db_port, self.db_dump)
        os.system(cmd)
        print("=> PostgreSQL dump loaded")


    def _InitializeDatabaseFromScratch(self):
        pg_dir = os.environ['PG_DIR']
        pg_bin = os.path.join(pg_dir, 'bin')
        pg_psql = os.path.join(pg_bin, 'psql')
        print("=> Initializing database tables...")
        for product in reversed(self.products):
            sqlfile = os.path.join(self.path, product.name, 'db', 'init', 'db_schema.sql')
            if os.path.exists(sqlfile):
                if os.system('%s -q -v ON_ERROR_STOP=1 -p %s %s -U %s -f %s'\
                             %(pg_psql, self.db_port, self.db_name, self.db_user, sqlfile)) != 0:
                    print("Error: can't init DB schema! Aborting...")
                    os.system('%s -D %s/var/db --silent stop'%(pg_ctl, self.target))
                    sys.exit(1)

        sys.stdout.flush()
        print("=> PostgreSQL DB loaded")

    def _LoadAndLearn(self):
        varpkl = os.path.join(self.target, 'var', 'pkl')
        self._Makedirs(varpkl)

        Bot.Bot().varhome = os.path.join(self.target, 'var')
        # Setup predefined classifiers
        pg_dir = os.environ['PG_DIR']
        pg_bin = os.path.join(pg_dir, 'bin')
        pg_psql = os.path.join(pg_bin, 'psql')
        for fname in os.listdir(varpkl):
            name = os.path.basename(fname).split('.')[0]
            obj = MLObject(name)
            obj.LoadPickle()
            for lang in obj._models:
                variable = 'classifier.%s.%s.learn'%(name, lang)
                query = """insert into kbot_settings (variable, value) values(\'%s\', \'%s\')
                           on conflict (variable) do update set value=EXCLUDED.value
                        """%(variable, utils.GetStringTime(datetime.datetime.now()))
                if self.db_internal:
                    if os.system('%s -q -p %s %s -c "%s"'%(pg_psql, self.db_port, self.db_name, query)) != 0:
                        print("Error: can't save predefined classifiers! Aborting...")
                        os.system('%s -D %s/var/db --silent stop'%(self.pg_ctl, self.target))
                        sys.exit(1)
                elif os.system("""export PGPASSWORD='%s';%s -q -h %s -p %s -d %s -U %s -c "%s"
                               """%(self.db_password, pg_psql, self.db_host, self.db_port, self.db_name, self.db_user, query)) != 0:
                    print("Error: can't save predefined classifiers! Aborting...")
                    sys.exit(1)

        if not self.no_load and not self.db_dump:
            print("Loading data...")
            sys.stdout.flush()
            if os.system('%s/bin/kbot.sh load'%self.target) != 0:
                print("Error during loading! Aborting...")
                os.system('%s -D %s/var/db --silent stop'%(self.pg_ctl, self.target))
                sys.exit(1)

            if self.admin_password:
                _db_request = f"UPDATE users_im_account SET pwd=\'{self.admin_password}\' "
                _db_request += "WHERE user_id=(SELECT users.user_id FROM users WHERE users.user_name=\'admin\')"
                if self.db_internal:
                    if os.system('%s -q -p %s %s -U %s -c "%s"'\
                                 %(pg_psql, self.db_port, self.db_name, self.db_user, _db_request)) != 0:
                        print("Error: can't setup admin password! Aborting...")
                        os.system('%s -D %s/var/db --silent stop'%(self.pg_ctl, self.target))
                        sys.exit(1)
                # setup admin password
                elif os.system('export PGPASSWORD=\'%s\';%s -q -h %s -p %s %s -U %s -c "%s"'\
                                 %(self.db_password, pg_psql, self.db_host, self.db_port, self.db_name, self.db_user, _db_request)) != 0:
                    print("Error: can't setup admin password! Aborting...")
                    sys.exit(1)

        if not self.no_learn:
            print("Learning models...")
            if os.system('%s/bin/kbot.sh learn'%self.target) != 0:
                print("Error during learning! Aborting...")
                os.system('%s -D %s/var/db --silent stop'%(self.pg_ctl, self.target))
                sys.exit(1)

    def _StartInstallation(self):
        print("You are about to install Konverso Kbot")
        print("This installer will guide you through the initial installation process")
        if not self._AskYN("Continue the installation? [yes]: "):
            print("OK, interruping the installation")
            sys.exit(1)

    def _SelectInstallationType(self):
        print("Basic installation will install Kbot components all together with default settings")
        print("Advanced installation allows you to set a specific parameters for each component")
        self.basic_installation = self._AskYN(
            "Continue with basic installation? [yes]: ")

    def _FinishInstallation(self):
        self._Makedirs(os.path.join(self.target, 'var', 'web_cache'))

        if self.db_internal:
            print("Shutting down PostgreSQL server...")
            os.system('%s -D %s/var/db --silent stop' %
                      (self.pg_ctl, self.target))

        local_kbot_conf = os.path.join(self.target, 'conf', 'kbot.conf')
        if os.path.exists(local_kbot_conf):
            # Set permission for kbot.conf (available only for current user)
            os.chmod(os.path.join(self.target, 'conf', 'kbot.conf'), 0o600)

        # Create history.txt with the date of installation
        # SHOULDN'T WE DO THIS INSIDE THE RUN.LOG INSTEAD ?
        ts = time.time()
        with open(os.path.join(self.target, 'var', 'run.log'), 'w+', encoding='utf8') as fd:
            fd.write("%s: Initial work area setup\n" % datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d'))

        print("\n\nCongratulation!")
        print("Now you can start Kbot using command '%s start'"%(os.path.join(self.target, 'bin', 'kbot.sh')))
        print("and configure it via Web UI here: %s/admin" % self.kbot_external_root_url)

        # move install.log file to work-area/logs/ directory
        if os.path.exists(self.installer_log_file):
            shutil.move(self.installer_log_file, os.path.join(self.target, 'logs'))

    def _GetProducts(self):
        basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        names = [x for x in os.listdir(basedir) if self._GetProduct(os.path.join(basedir, x), x)]
        if not self.product:
            product = input("Which product to install (Choose one: %s): "%(', '.join(names))).strip()
        else:
            product = self.product

        if product:
            self._GetProductPath(product)
        else:
            print("Nothing to install")
            sys.exit(1)

    def _GetProductPath(self, name):

        installer = self.path
        work = self.workarea
        deps.build_dependency_file(name, installer, "/tmp/products.json")
        self.products.populate(products_definition_file="/tmp/products.json")

    def _GetProduct(self, path, name):
        if path:
            if os.path.exists(path):
                description_xml_path = os.path.join(path, 'description.xml')

                if os.path.exists(description_xml_path):
                    # Use the installer product class to load the product definition
                    product_def =  BaseProduct.from_xml_file(description_xml_path)
                    json_def = json.loads(product_def.to_json())

                    # Create a kbot product instance
                    product = Product()
                    product.Update(json_def)
                    product.filename = description_xml_path
                    product.dirname = path
                    return product
            else:
                print("Path not found:", path)
        else:
            print("No path:", path)

        return None

    def _Copy(self, src, dst):
        if not os.path.exists(dst) and os.path.exists(src):
            shutil.copyfile(src, dst)

    def _LinkAbs(self, src, dst):
        if not os.path.exists(dst) and os.path.exists(src):
            os.symlink(src, dst)

    pythonexts = ('.so', '.py')

    def _Link(self, src, dst):
        if os.path.exists(src):
            _, srcext = os.path.splitext(src)
            dstroot, dstext = os.path.splitext(dst)
            if srcext in self.pythonexts and dstext in self.pythonexts:
                for ext in self.pythonexts:
                    dstname = '%s%s' % (dstroot, ext)
                    if os.path.exists(dstname):
                        if self.update and os.path.islink(dstname) and not os.path.samefile(src, dstname):
                            if self.silent or self._AskYN("Wrong link '%s'. Recreate it? [yes]" % (dstname)):
                                os.unlink(dstname)
                        else:
                            break
                else:
                    if not os.path.exists(dst):
                        os.symlink(self._NewSrc(src, dst), dst)
            else:
                if self.update and os.path.islink(dst):
                    targetpath = os.readlink(dst)
                    # Get absolute path
                    if not targetpath.startswith("/"):
                        targetpath = os.path.join(os.environ['KBOT_HOME'], targetpath.strip("./"))

                    if not os.path.exists(targetpath):
                        if self.silent or self._AskYN("Broken link '%s'. Remove it? [yes]" % (dst)):
                            os.unlink(dst)
                    elif not os.path.samefile(src, dst):
                        if self.silent or self._AskYN("Wrong link '%s'. Recreate it? [yes]" % (dst)):
                            os.unlink(dst)
                if not os.path.exists(dst):
                    os.symlink(self._NewSrc(src, dst), dst)

    #pylint: disable=too-many-positional-arguments
    def _LinkProductFilesToDir(self, relpath, dst, linkdirs=None, exts=None, ignoredirs=None):
        if linkdirs is None:
            linkdirs = []
        if ignoredirs is None:
            ignoredirs = []
        self._Makedirs(dst)
        # Check broken links
        if self.update:
            self._ValidateLinksInDir(dst)

        dstdirs = [d for d in os.listdir(dst) if os.path.isdir(os.path.join(dst, d))]
        for fullname in self.products.get_files(relpath, '*', exts=exts):
            if os.path.exists(fullname):
                fname = os.path.basename(fullname)
                if os.path.isdir(fullname):
                    if fname in dstdirs:
                        dstdirs.remove(fname)
                    if fname in linkdirs:
                        self._Link(fullname,
                                   os.path.join(dst, fname))
                    else:
                        self._LinkProductFilesToDir(os.path.join(relpath, fname),
                                                    os.path.join(dst, fname),
                                                    linkdirs, exts, ignoredirs)
                elif os.path.isfile(fullname):
                    self._Link(fullname,
                               os.path.join(dst, fname))
        for dstdir in dstdirs:
            if not dstdir.startswith('__') and dstdir not in ignoredirs: # Don't remove '__pycache__' directories
                realdir = os.path.join(relpath, dstdir)
                if os.path.islink(realdir):
                    print(f"Warning: Found plain folder in core/python/{dstdir}. This is potentially unsafe. Should you save this code ?")
                elif os.path.isdir(realdir):
                    if self.silent or self._AskYN("Not used directory '%s'. Remove it? [yes]" % realdir):
                        shutil.rmtree(os.path.join(dst, dstdir))
                else:
                    print(f"Error: Unsupported folder type. Review 'core/python/{dstdir}'")

    def _CopyProductFilesToDir(self, relpath, dst):

        self._Makedirs(dst)
        # Check deleted files
        for fullname in self.products.get_files(relpath, '*'):
            if os.path.exists(fullname):
                fname = os.path.basename(fullname)
                if os.path.isdir(fullname):
                    self._CopyProductFilesToDir(os.path.join(relpath, fname),
                                                os.path.join(dst, fname))
                elif os.path.isfile(fullname):
                    fdest = os.path.join(dst, fname)
                    if self.update and os.path.exists(fdest):
                        os.unlink(fdest)
                    self._Copy(fullname, fdest)

    def _LinkDir(self, src, dst, linkdirs=None):
        if linkdirs is None:
            linkdirs = []
        self._Makedirs(dst)
        if os.path.exists(src):
            for fname in os.listdir(src):
                fullname = os.path.join(src, fname)
                if os.path.isdir(fullname):
                    if fname in linkdirs:
                        self._Link(fullname,
                                   os.path.join(dst, fname))
                    else:
                        self._LinkDir(fullname,
                                      os.path.join(dst, fname),
                                      linkdirs)
                elif os.path.isfile(fullname):
                    self._Link(fullname,
                               os.path.join(dst, fname))

    def _ValidateLinksInDir(self, dirname):
        for fname in os.listdir(dirname):
            fullname = os.path.join(dirname, fname)
            if os.path.islink(fullname):
                targetpath = os.readlink(fullname)
                if not os.path.isabs(targetpath):
                    targetpath = os.path.join(dirname, targetpath)
                if not os.path.exists(targetpath):
                    if self.silent or self._AskYN("Broken link '%s'. Remove it? [yes]" % fullname):
                        os.unlink(fullname)

    def _Makedirs(self, dst):
        if not os.path.exists(dst):
            os.makedirs(dst)

    def _NewSrc(self, src, dst):
        # We return absolute path links
        return src

    def _AskYN(self, question, default='y'):
        while True:
            if self.default:
                answer = "y"
            else:
                answer = input(question).strip().lower() or default
            if answer in {'y', 'yes'}:
                return True
            if answer in {'n', 'no'}:
                return False
            print('Answer either "y" or "n".')

    def _AskPort(self, question, default, ptype, limit=True):
        while True:
            answer = input("%s [%s]: "%(question, default)).strip() or default
            if answer.isdigit():
                port = int(answer)
                if limit and port < 1024:
                    print("Do not use port number below 1024 as it requires root privileges")
                elif limit and port > 65535:
                    print("Max port number is 65535.")
                elif (ptype == 'http' and answer == self.https_port) or \
                   (ptype == 'https' and answer == self.http_port):
                    print("HTTP and HTTPS ports could not be the same")
                else:
                    return answer
            else:
                print("Wrong port number")

    def _CommandOutput(self, command):
        res = subprocess.check_output(command, stderr=subprocess.STDOUT).strip().decode('utf-8')
        #if res:
        #    print("Failed running", command)
        return res

def usage():
    print("""

  To install kbot:
      installer/kbot/install.sh --product ithd
                                [--path /home/konverso/dev/installer]
                                [--workarea /home/konverso/dev/work]
                                [--accept-licence] [--default] 
  
  To update the product links:
       installer/kbot/install.sh [-s|--silent] -u|--update


  Details of the parameters and associated specs and constaints:

  --product: Mandatory. Define the target product to be installed. 
             All related product dependencies are automatically calculated.

  --path or -p: Optional. The path to be used for the retrieving the product binaries
             If unset, the user will be prompted for each production installation path

  --accept-licence: Optional. Can be used to explicity indicate license approval
             and avoid the interactive prompt for the license approval

  ---default or -d: Optional. Use the default values, to avoid any interaction, specifically, this will include: 
             - default db name/user/password/port
             - default https port
             - default URL, based on the current hostname
             - etc.

  --hostname: Optional. Hostname to use. Should be the external hostname as it will also be used
            for external URLs references.

   To run a automatic (non interactive installer), make sure to include at the least the following flags:
       --product --path --accept-licence --default --hostname

""")


if __name__ == '__main__':

    import argparse
    try:
        parser = argparse.ArgumentParser(prog='setup_workarea')

        #
        # The installation related arguments
        #
        parser.add_argument('--product', help="Top level product", dest='product', required=False)
        parser.add_argument('-p', '--path', help="Default path for the products", dest='path', required=False)
        parser.add_argument('--secret', help="Default secret password for the admin", dest='secret', required=False)
        parser.add_argument('-w', '--workarea', help="Default work-area path", dest='workarea', required=False)
        parser.add_argument('--accept-licence', help="Accept the license agreement", dest='license', action="store_true", required=False, default=False)
        parser.add_argument('--hostname', help="Default hostname", dest='hostname', required=False)
        parser.add_argument('-d', '--default', help="Use the default answer to reduce or avoid any interaction",
                            action="store_true", dest='default', required=False, default=False)
        parser.add_argument('--no-learn', help="Do not learn following the setup", dest='no_learn', action="store_true", required=False, default=False)
        parser.add_argument('--no-load', help="Do not load following the setup", dest='no_load', action="store_true", required=False, default=False)
        parser.add_argument('--no-password', help="Do not require a password", dest='no_password', action="store_true", required=False, default=False)
        parser.add_argument('--db-dump', help="Optional dump file to load on work area creation", dest='db_dump', required=False)

        #
        # Optional Postgres arguments
        # (KB-13121)
        parser.add_argument('--postgres-host', help="Postgres hostname or IP", dest='db_host', required=False)
        parser.add_argument('--postgres-port', help="Postgres port", dest='db_port', required=False)
        parser.add_argument('--postgres-user', help="Postgres user", dest='db_user', required=False)
        parser.add_argument('--postgres-password', help="Postgres password", dest='db_password', required=False)
        parser.add_argument('--postgres-db', help="Postgres DB name", dest='db_name', required=False)

        #
        # The relink (update) related arguments
        #
        parser.add_argument('-t', '--tree', help="Display the product tree",  action="store_true", dest='show_tree', required=False, default=False)
        parser.add_argument('-s', '--silent', help="Silent", action="store_true", dest='silent', required=False, default=False)
        parser.add_argument('-u', '--update', help="Update links",  action="store_true", dest='update', required=False, default=False)

        _result = parser.parse_args()

        # Case of the relink
        if _result.show_tree:
            if not _result.product:
                print("Missing the mandatory -p flag")
                sys.exit(1)

            Installer().ShowTree(_result.product)
            sys.exit(0)

        # Case of the relink (bin/linkproducts.sh)
        if _result.update:
            installer = Installer(path=_result.path, workarea=_result.workarea)
            installer.Update(_result.silent)
            sys.exit(0)

        # Case of the kbot installation
        if _result.product:

            installer = Installer(product=_result.product, path=_result.path, secret=_result.secret, workarea=_result.workarea,
                                  license=_result.license, hostname=_result.hostname, default=_result.default,
                                  no_load=_result.no_load, no_learn=_result.no_learn, no_password=_result.no_password,
                                  db_dump=_result.db_dump)

            # Update the installer values based on some argument parameters
            for _param in ('db_host', 'db_port', 'db_user', 'db_password', 'db_name'):
                if getattr(_result, _param):
                    setattr(installer, _param, getattr(_result, _param))

            if installer.db_host:
                installer.db_internal = False

            installer.Run()


        else:
            usage()
            sys.exit(1)

    except Exception as _e:
        usage()
        raise
