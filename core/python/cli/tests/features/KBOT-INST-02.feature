# language: en
Feature: KBOT-INST-02 Installation

  Background:
    Given the environment variable NEXUS_USERNAME is "kbot"
    And the environment variable NEXUS_PASSWORD is "secret"
    And the environment variable KBOT_ADMIN_PASSWORD is "K0nversOK!"
    And the environment variable PG_DIR is "/opt/pg16"
    And the storage holds the product "kbot" version "2026.01" at commit "c0ffee0003" of branch "release-2025.03-dev"
    And the storage holds the product "base-product" version "2026.01" at commit "c0ffee0002" of branch "release-2025.03-dev" with parents "kbot"
    And the storage holds the product "site-konverso" version "2026.01" at commit "c0ffee0001" of branch "release-2025.03-dev" with parents "base-product, kbot"

  @since-2026.01 @AC-KBOT-INST-02-01 @BR-04 @BR-06 @BR-14 @BR-29 @BR-35 @BR-44
  Scenario: Install a product with its dependencies on an internal database (nominal case) (BR-04, BR-06, BR-14, BR-29, BR-35, BR-44)
    Given the operator's home directory is "/home/kbot"
    And the directory "/home/kbot/dev/work" does not exist
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev"
    Then the product "site-konverso" is downloaded from storage at branch "release-2025.03-dev"
    And the product "base-product" is downloaded from storage at branch "release-2025.03-dev"
    And the product "kbot" is downloaded from storage at branch "release-2025.03-dev"
    And the file "/home/kbot/dev/installer/site-konverso/description.xml" contains "site-konverso"
    And the file "/home/kbot/dev/installer/base-product/description.xml" contains "base-product"
    And the file "/home/kbot/dev/installer/kbot/description.xml" contains "kbot"
    And the file "/home/kbot/dev/work/var/products.json" contains "site-konverso"
    And the command ran, in order:
      | command                                                                          |
      | /home/kbot/dev/work/bin/python.sh -m utils.License /home/kbot/dev/work/var/license.key |
      | /opt/pg16/bin/pg_ctl -D /home/kbot/dev/work/var/db                               |
      | /opt/pg16/bin/psql                                                               |
      | /home/kbot/dev/work/bin/core.sh load --profiles                                  |
    And the file "/home/kbot/dev/work/var/db/PG_VERSION" contains "16"
    And the schema files were applied in order:
      | file                                                         |
      | /home/kbot/dev/installer/kbot/db/init/db_schema.sql          |
      | /home/kbot/dev/installer/base-product/db/init/db_schema.sql  |
      | /home/kbot/dev/installer/site-konverso/db/init/db_schema.sql |
    And the output ends with "Installation completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-02-02 @BR-03
  Scenario: Install every product of a bundle without a version (BR-03)
    Given the storage holds the bundle "ev-basic-00018" version "2025.03.0018" pinning:
      | product       | commit     | branch              |
      | kbot          | c0ffee0003 | release-2025.03-dev |
      | base-product  | c0ffee0002 | release-2025.03-dev |
      | site-konverso | c0ffee0001 | release-2025.03-dev |
    When the operator runs "kbot-installer install -b ev-basic-00018 -p site-konverso -w /home/kbot/dev/work"
    Then the product "kbot" is downloaded from storage at commit "c0ffee0003" of branch "release-2025.03-dev"
    And the product "base-product" is downloaded from storage at commit "c0ffee0002" of branch "release-2025.03-dev"
    And the product "site-konverso" is downloaded from storage at commit "c0ffee0001" of branch "release-2025.03-dev"
    And the output does not contain "-v/--version"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-02-03 @BR-05
  Scenario: Pass provider and storage options to the download step (BR-05)
    Given the environment variable NEXUS_USERNAME is not set
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev --provider github --provider storage --storage s3 -w /home/kbot/dev/work"
    Then the git providers are tried in order:
      | provider |
      | github   |
    And the product "site-konverso" is downloaded from the "artifacts" area of the "s3" storage
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-02-04 @BR-01
  Scenario: Refuse an install without product (BR-01, error)
    When the operator runs "kbot-installer install -v 2025.03-dev"
    Then the output contains "Missing option '-p' / '--product'."
    And the exit code is 2

  @since-2026.01 @AC-KBOT-INST-02-05 @BR-02
  Scenario: Refuse a product install without version (BR-02, error)
    When the operator runs "kbot-installer install -p site-konverso -w /home/kbot/dev/work"
    Then the output contains "Option '-v/--version' is required when installing a product without '-b/--bundle'."
    And nothing is downloaded
    And the exit code is 2

  @since-2026.01 @AC-KBOT-INST-02-06 @BR-08
  Scenario: Cancel the install when the workarea already exists (BR-08, error)
    Given the directory "/home/kbot/dev/work" exists
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the error output contains "Workarea directory '/home/kbot/dev/work' already exists. Installation cancelled."
    And nothing is downloaded
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-02-07 @BR-09 @BR-10
  Scenario: Recreate an existing workarea with --force-recreate (BR-09, BR-10)
    Given the directory "/home/kbot/dev/work/var/db" exists
    And the file "/home/kbot/dev/work/stale_marker" contains "old"
    And the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work --force-recreate"
    Then the output contains "Deleting existing workarea directory '/home/kbot/dev/work' (--force-recreate)..."
    And "/home/kbot/dev/work/stale_marker" no longer exists
    And the file "/home/kbot/dev/installer/kbot/description.xml" contains "kbot"
    And the product "site-konverso" is downloaded from storage at branch "release-2025.03-dev"

  @since-2026.01 @AC-KBOT-INST-02-08 @BR-11 @BR-13
  Scenario Outline: Resolve the kbot admin password (BR-11, BR-13)
    Given the environment variable KBOT_ADMIN_PASSWORD <env>
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work --no-admin-password"
    Then the password of "admin" in "kbot_db" verifies <password>
    And the output <display> "Generated kbot admin password:"

    Examples:
      | env               | password                                                   | display          | rule  |
      | is "K0nversOK!"   | "K0nversOK!"                                               | does not contain | BR-11 |
      | is not set        | the password printed after "Generated kbot admin password: " | contains         | BR-13 |

  @since-2026.01 @AC-KBOT-INST-02-09 @BR-12
  Scenario: Refuse an install without admin password (BR-12, error)
    Given the environment variable KBOT_ADMIN_PASSWORD is not set
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the output contains "Admin password required: set 'KBOT_ADMIN_PASSWORD' or use '--no-admin-password'."
    And nothing is downloaded
    And the exit code is 2

  @since-2026.01 @AC-KBOT-INST-02-10 @BR-15
  Scenario: Lay out every product present in the installer directory (BR-15)
    Given the installer directory "/home/kbot/dev/installer" holds the product "legacy-addon" of type "solution"
    And the file "/home/kbot/dev/installer/legacy-addon/db/init/db_schema.sql" contains "CREATE TABLE legacy_addon_data (id int);"
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the file "/home/kbot/dev/work/var/products.json" contains "legacy-addon"
    And the schema files were applied in order:
      | file                                                         |
      | /home/kbot/dev/installer/kbot/db/init/db_schema.sql          |
      | /home/kbot/dev/installer/legacy-addon/db/init/db_schema.sql  |
      | /home/kbot/dev/installer/base-product/db/init/db_schema.sql  |
      | /home/kbot/dev/installer/site-konverso/db/init/db_schema.sql |

  @since-2026.01 @AC-KBOT-INST-02-11 @BR-16
  Scenario Outline: Choose the workarea product layout from the kbot version (BR-16)
    Given the storage holds the product "kbot" version "<kbot version>" at commit "c0ffee0003" of branch "release-2025.03-dev"
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then <layout>
    And <other layout>

    Examples:
      | kbot version | layout                                                                          | other layout                                                                 | rule  |
      | 2026.01      | the file "/home/kbot/dev/work/var/products.json" contains "kbot"                | the directory "/home/kbot/dev/work/products" does not exist                  | BR-16 |
      | 2025.03      | "/home/kbot/dev/work/products/kbot" is a symlink to "/home/kbot/dev/installer/kbot" | the file "/home/kbot/dev/work/conf/kbot.conf" contains "Kbot configuration file" | BR-16 |

  @since-2026.01 @AC-KBOT-INST-02-12 @BR-17
  Scenario: Create the workarea runtime directories (BR-17)
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the directory "/home/kbot/dev/work/logs/httpd" exists
    And the directory "/home/kbot/dev/work/var/pkl" exists
    And the directory "/home/kbot/dev/work/var/pkl/storage" exists
    And the directory "/home/kbot/dev/work/var/pkl/test_results" exists
    And the directory "/home/kbot/dev/work/var/cache" exists

  @since-2026.01 @AC-KBOT-INST-02-13 @BR-18 @BR-14
  Scenario: Stop the install on an invalid license (BR-18, BR-14, error)
    Given the license "/home/kbot/dev/work/var/license.key" is invalid with "ERROR : LICENSE is expired."
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the error output contains "Error installing product: Invalid license '/home/kbot/dev/work/var/license.key': ERROR : LICENSE is expired."
    And the command did not run "pip3.sh"
    And the command did not run "pg_ctl"
    And the database is not contacted
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-02-14 @BR-19
  Scenario: Install the products' Python requirements (BR-19)
    Given the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution" with parents "kbot"
    And the file "/home/kbot/dev/installer/acme/requirements.txt" contains "requests"
    And the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/installer/kbot/bin/pip3.sh" contains "#!/bin/sh"
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.13" and PostgreSQL "16.4"
    When the operator runs "kbot-installer install -p acme -v 2025.03-dev -w /home/kbot/dev/work"
    Then the command ran "/home/kbot/dev/installer/kbot/bin/pip3.sh install -r /home/kbot/dev/installer/acme/requirements.txt"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-02-15 @BR-20
  Scenario: Skip the products' Python requirements (BR-20)
    Given the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution" with parents "kbot"
    And the file "/home/kbot/dev/installer/acme/requirements.txt" contains "requests"
    And the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/installer/kbot/bin/pip3.sh" contains "#!/bin/sh"
    When the operator runs "kbot-installer install -p acme -v 2025.03-dev -w /home/kbot/dev/work --skip-python-requirements"
    Then the command did not run "pip3.sh"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-02-16 @BR-21
  Scenario: Skip the Python requirements when pip3.sh is missing (BR-21)
    Given the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution" with parents "kbot"
    And the file "/home/kbot/dev/installer/acme/requirements.txt" contains "requests"
    When the operator runs "kbot-installer install -p acme -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the warning "Skipping product Python requirements: '/home/kbot/dev/installer/kbot/bin/pip3.sh' not found." is logged
    And the command ran "/opt/pg16/bin/pg_ctl -D /home/kbot/dev/work/var/db"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-02-17 @BR-22
  Scenario: Stop the install when the 3rdparty Python is missing (BR-22, error)
    Given the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution" with parents "kbot"
    And the file "/home/kbot/dev/installer/acme/requirements.txt" contains "requests"
    And the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/installer/kbot/bin/pip3.sh" contains "#!/bin/sh"
    And the directory "/home/kbot/dev/installer/3rdparty" does not exist
    When the operator runs "kbot-installer install -p acme -v 2025.03-dev -w /home/kbot/dev/work"
    Then the error output contains "Cannot install Python requirements: the 3rdparty Python is missing from '/home/kbot/dev/installer'"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-02-18 @BR-23
  Scenario: Stop the install when a requirements installation fails (BR-23, error)
    Given the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution" with parents "kbot"
    And the file "/home/kbot/dev/installer/acme/requirements.txt" contains "requests"
    And the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/installer/kbot/bin/pip3.sh" contains "#!/bin/sh"
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.13" and PostgreSQL "16.4"
    And the program "pip3.sh" exits with code 1
    When the operator runs "kbot-installer install -p acme -v 2025.03-dev -w /home/kbot/dev/work"
    Then the error output contains "Failed to install Python requirements for 'acme' (exit 1)."
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-02-19 @BR-24 @BR-25
  Scenario Outline: Resolve the database password (BR-24, BR-25)
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work <options>"
    Then the user "kbot_db_user" on "localhost" port 5432 has <password>
    And the output <display> "Generated database password for 'kbot_db_user':"

    Examples:
      | options                               | password                                                                  | display          | rule  |
      |                                       | the password "kbot_db_pwd"                                                | does not contain | BR-24 |
      | --db-password S3cret                  | the password "S3cret"                                                     | does not contain | BR-24 |
      | --db-password S3cret --no-db-password | the password "S3cret"                                                     | does not contain | BR-24 |
      | --no-db-password                      | the password printed after "Generated database password for 'kbot_db_user': " | contains         | BR-25 |

  @since-2026.01 @AC-KBOT-INST-02-20 @BR-26 @BR-31 @BR-32
  Scenario: Create the internal role and database with the default settings (BR-26, BR-31, BR-32)
    Given the environment variable PG_ADMIN_PASSWORD is not set
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the database server "localhost" port 5432 was contacted as "postgres" with the password "postgres"
    And the user "kbot_db_user" on "localhost" port 5432 has the password "kbot_db_pwd"
    And the database "kbot_db" exists, owned by "kbot_db_user"
    And the internal PostgreSQL server of "/home/kbot/dev/work" is running on port 5432

  @since-2026.01 @AC-KBOT-INST-02-21 @BR-27
  Scenario Outline: Resolve the PostgreSQL directory (BR-27)
    Given the environment variable PG_DIR <env>
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.13" and PostgreSQL "11.5"
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the command ran "<pg dir>/psql"

    Examples:
      | env              | pg dir                                                  | rule  |
      | is "/opt/pg16"   | /opt/pg16/bin                                           | BR-27 |
      | is not set       | /home/kbot/dev/installer/3rdparty/postgresql-11.5/bin   | BR-27 |

  @since-2026.01 @AC-KBOT-INST-02-22 @BR-28
  Scenario: Stop the install when PostgreSQL cannot be located (BR-28, error)
    Given the environment variable PG_DIR is not set
    And the directory "/home/kbot/dev/installer/3rdparty" does not exist
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the output contains "Unable to locate PostgreSQL: set the 'PG_DIR' environment variable, or ensure '/home/kbot/dev/installer/3rdparty/versions.env' exists and defines 'PG_DIR'."
    And the exit code is 2

  @since-2026.01 @AC-KBOT-INST-02-23 @BR-30
  Scenario: Stop the install when the internal database port is in use (BR-30, error)
    Given port 5432 on localhost is used by process 4242
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the error output contains "Cannot start PostgreSQL: port 5432 on localhost is already in use (in use by PID 4242, possibly a leftover process from a previous run)."
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-02-24 @BR-33
  Scenario: Install on an external database (BR-33)
    Given the database "kbot_db" on "db.example.com" port 5432 accepts the user "kbot_db_user" with the password "S3cret"
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work --db-host db.example.com --db-password S3cret"
    Then the directory "/home/kbot/dev/work/var/db" does not exist
    And the command did not run "pg_ctl"
    And no role and no database is created on "db.example.com"
    And the command ran "/opt/pg16/bin/psql -v ON_ERROR_STOP=1 -q -h db.example.com -p 5432 -U kbot_db_user -d kbot_db -f"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-02-25 @BR-34
  Scenario: Keep a database that already has tables (BR-34)
    Given the database "kbot_db" on "db.example.com" port 5432 accepts the user "kbot_db_user" with the password "S3cret"
    And the database "kbot_db" has tables
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work --db-host db.example.com --db-password S3cret"
    Then the command did not run "psql"
    And the command ran "/home/kbot/dev/work/bin/core.sh load --profiles"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-02-26 @BR-36
  Scenario: Stop the install when a schema file fails (BR-36, error)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/installer/kbot/db/init/db_schema.sql" contains "SYNTAX ERROR"
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the error output contains "Error installing product: Failed to apply SQL file /home/kbot/dev/installer/kbot/db/init/db_schema.sql:"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-02-27 @BR-37
  Scenario: Create the schema version table without a version (BR-37)
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the database "kbot_db" has the table "__schema_version"
    And the database "kbot_db" records no schema version

  @since-2026.01 @AC-KBOT-INST-02-28 @BR-38 @BR-39
  Scenario Outline: Load the initial data (BR-38, BR-39)
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work <options>"
    Then the command ran "<script>"

    Examples:
      | options      | script                                          | rule  |
      |              | /home/kbot/dev/work/bin/core.sh load --profiles | BR-38 |
      | --with-load  | /home/kbot/dev/work/bin/kbot.sh load            | BR-39 |

  @since-2026.01 @AC-KBOT-INST-02-29 @BR-40
  Scenario: Store the admin password hashed (BR-40)
    Given the environment variable KBOT_ADMIN_PASSWORD is "K0nversOK!"
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the password of "admin" in "kbot_db" verifies "K0nversOK!"

  @since-2026.01 @AC-KBOT-INST-02-30 @BR-41
  Scenario: Fail when the load creates no admin account (BR-41, error)
    Given the users load creates no "admin" account
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the error output contains "No 'admin' account found in the database: the users load (users.conf) did not create it."
    And the output does not contain "Installation completed successfully."
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-02-31 @BR-42
  Scenario: Train the models after the install (BR-42)
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work --with-learn"
    Then the password of "admin" in "kbot_db" is set before "/home/kbot/dev/work/bin/kbot.sh learn" runs

  @since-2026.01 @AC-KBOT-INST-02-32 @BR-43
  Scenario: Stop the install when a workarea script fails (BR-43, error)
    Given the program "kbot.sh learn" exits with code 1
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work --with-learn"
    Then the error output contains "'/home/kbot/dev/work/bin/kbot.sh learn' failed (exit 1)."
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-02-33 @BR-45 @BR-46
  Scenario: Leave a failed install in place (BR-45, BR-46, error)
    Given the program "kbot.sh load" exits with code 1
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work --with-load"
    Then the error output contains "Error installing product: '/home/kbot/dev/work/bin/kbot.sh load' failed (exit 1)."
    And the error output contains "Aborted!"
    And the exit code is 1
    And the directory "/home/kbot/dev/work" exists
    And the database "kbot_db" exists, owned by "kbot_db_user"
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work --with-load"
    Then the error output contains "Workarea directory '/home/kbot/dev/work' already exists. Installation cancelled."

  @since-2026.01 @AC-KBOT-INST-02-34 @BR-07
  Scenario: Show download details in verbose mode (BR-07)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the product "kbot" in "/home/kbot/dev/installer" was downloaded from storage at commit "c0ffee0003" of branch "release-2025.03-dev"
    When the operator runs "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work -V"
    Then the download table shows "kbot" from "storage (cached)" with status "⏭️ Skipped" and details "Already installed"
    And the output, apart from the download table, is the same as for "kbot-installer install -p site-konverso -v 2025.03-dev -i /home/kbot/dev/installer -w /home/kbot/dev/work" on a fresh workarea
