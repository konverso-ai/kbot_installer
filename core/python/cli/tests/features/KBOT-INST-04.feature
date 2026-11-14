# language: en
Feature: KBOT-INST-04 Release upgrade

  Background:
    Given the environment variable NEXUS_USERNAME is "kbot"
    And the environment variable NEXUS_PASSWORD is "secret"
    And a kbot workarea exists in "/home/kbot/dev/work"
    And the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the product "kbot" in "/home/kbot/dev/installer" was downloaded from storage at commit "c0ffee2503" of branch "release-2025.03-dev"
    And the installer directory "/home/kbot/dev/installer" holds the product "site-konverso" of type "solution" with parents "kbot"
    And the product "site-konverso" in "/home/kbot/dev/installer" was downloaded from storage at commit "c0ffee2501" of branch "release-2025.03-dev"
    And the product "site-konverso" in "/home/kbot/dev/installer" is at version "2025.03"
    And the storage holds the product "kbot" version "2026.01" at commit "c0ffee0003" of branch "release-2026.01-dev"
    And the storage holds the product "site-konverso" version "2026.01" at commit "c0ffee0001" of branch "release-2026.01-dev" with parents "kbot"

  @since-2026.01 @AC-KBOT-INST-04-01
  Scenario: Upgrade a product installation to a newer release (nominal case)
    Given the installer directory "/home/kbot/dev/installer" was not installed from a bundle
    And the operator will answer "y" to "Continue with upgrade?"
    And the operator will answer "y" to "Back up the database before upgrading?"
    And the operator will answer "" to "Backup file"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01"
    Then the question "Continue with upgrade?" is asked
    And the question "Back up the database before upgrading?" is asked
    And the question "Backup file" is asked
    And the database is dumped to "/home/kbot/dev/installer/backup_<YYYYMMDD_HHMMSS>.sql"
    And the product "site-konverso" is downloaded from storage at branch "release-2026.01-dev"
    And the product "kbot" is downloaded from storage at branch "release-2026.01-dev"
    And the file "/home/kbot/dev/installer/site-konverso/description.json" contains "c0ffee0001"
    And the file "/home/kbot/dev/installer/kbot/description.json" contains "c0ffee0003"
    And the command ran, in order:
      | command                                                               |
      | /home/kbot/dev/work/bin/pg.sh start                                   |
      | /home/kbot/dev/work/bin/dump_db.sh -f /home/kbot/dev/installer/backup_ |
      | /home/kbot/dev/work/bin/kbot.sh stop                                  |
      | /home/kbot/dev/work/bin/upgrade_db.sh                                 |
      | /home/kbot/dev/work/bin/upgrade_patch.sh                              |
      | /home/kbot/dev/work/bin/kbot.sh load                                  |
      | /home/kbot/dev/work/bin/kbot.sh restart                               |
    And the output ends with "Upgrade completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-02 @BR-01 @BR-02 @BR-03 @BR-04 @BR-05 @BR-06
  Scenario Outline: Inconsistent target or backup options are refused (BR-01, BR-02, BR-03, BR-04, BR-05, BR-06, error)
    Given the installer directory "/home/kbot/dev/installer" <install>
    When the operator runs "kbot-installer upgrade <options> -y"
    Then the output contains "<message>"
    And the exit code is 2

    Examples:
      | rule  | install                                                       | options                                                     | message                                                                                                                         |
      | BR-01 | was not installed from a bundle                               | -p site-konverso                                            | Options '-p/--product' and '-v/--version' are required to upgrade a product installation.                                       |
      | BR-02 | was installed from bundle "ev-basic" version "2025.03.0010"   | -p site-konverso -v 2026.01                                 | '/home/kbot/dev/installer' was installed from a bundle: upgrade it with '-v/--version' or '-b/--bundle', without '-p/--product'. |
      | BR-03 | was installed from bundle "ev-basic" version "2025.03.0010"   |                                                             | Option '-v/--version' is required.                                                                                              |
      | BR-04 | was not installed from a bundle                               | -b ev-basic-2026.01.0003 -v 2026.01                         | '-b/--bundle' names the exact bundle to upgrade to: do not combine it with '-p/--product' or '-v/--version'.                    |
      | BR-05 | was not installed from a bundle                               | -p site-konverso -v 2026.01 --backup-file x.sql --no-backup | Options '--backup-file' and '--no-backup' are mutually exclusive.                                                               |
      | BR-06 | was not installed from a bundle                               | -b ev-basic-2026.01.0003 -B KB-1                            | Option '-B/--branch' requires '-v/--version'.                                                                                   |

  @since-2026.01 @AC-KBOT-INST-04-03 @BR-07
  Scenario: An option error changes nothing (BR-07, error)
    When the operator runs "kbot-installer upgrade -p site-konverso -B KB-1 -y"
    Then the output contains "Option '-B/--branch' requires '-v/--version'."
    And the exit code is 2
    And the storage is not read
    And nothing is downloaded
    And no process is run

  @since-2026.01 @AC-KBOT-INST-04-04 @BR-08
  Scenario: The workarea must be a Kbot workarea (BR-08, error)
    Given the directory "/tmp/empty" exists
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 -w /tmp/empty -y"
    Then the output contains "'/tmp/empty' is not a kbot workarea directory (no 'products/kbot' nor 'var/products.json')."
    And the exit code is 2
    And nothing is downloaded
    And no process is run

  @since-2026.01 @AC-KBOT-INST-04-05 @BR-09 @BR-25
  Scenario: A bundle installation upgrades to the latest bundle of its name for the version (BR-09, BR-25)
    Given the installer directory "/home/kbot/dev/installer" was installed from bundle "ev-basic" version "2025.03.0010"
    And the storage holds the bundle "ev-basic-2026.01.0003" version "2026.01.0003" pinning:
      | product       | commit     | branch              |
      | kbot          | c0ffee0003 | release-2026.01-dev |
      | site-konverso | c0ffee0001 | release-2026.01-dev |
    And the storage holds the bundle "ev-basic-2026.01.0005" version "2026.01.0005" pinning:
      | product       | commit     | branch              |
      | kbot          | c0ffee0003 | release-2026.01-dev |
      | site-konverso | c0ffee0001 | release-2026.01-dev |
    And the operator will answer "n" to "Continue with upgrade?"
    When the operator runs "kbot-installer upgrade -v 2026.01"
    Then the output contains "Upgrading '/home/kbot/dev/installer' and '/home/kbot/dev/work' to bundle ev-basic-2026.01.0005 (branch release-2026.01-dev)."
    And the question "Continue with upgrade?" is asked

  @since-2026.01 @AC-KBOT-INST-04-06 @BR-11
  Scenario: An exact bundle descriptor is the target (BR-11)
    Given the installer directory "/home/kbot/dev/installer" was installed from bundle "ev-basic" version "2025.03.0010"
    And the storage holds the bundle "ev-basic-2026.01.0003" version "2026.01.0003" pinning:
      | product       | commit     | branch              |
      | kbot          | c0ffee0003 | release-2026.01-dev |
      | site-konverso | c0ffee0001 | release-2026.01-dev |
    And the storage holds the bundle "ev-basic-2026.01.0005" version "2026.01.0005" pinning:
      | product       | commit     | branch              |
      | kbot          | c0ffee0005 | release-2026.01-dev |
      | site-konverso | c0ffee0005 | release-2026.01-dev |
    When the operator runs "kbot-installer upgrade -b ev-basic-2026.01.0003 -y"
    Then the output contains "to bundle ev-basic-2026.01.0003 (branch release-2026.01-dev)."
    And the product "kbot" is downloaded from storage at commit "c0ffee0003" of branch "release-2026.01-dev"
    And the product "site-konverso" is downloaded from storage at commit "c0ffee0001" of branch "release-2026.01-dev"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-07 @BR-10 @BR-11 @BR-12 @BR-13 @BR-14 @BR-15
  Scenario Outline: An unknown or older target cancels the upgrade (BR-10, BR-11, BR-12, BR-13, BR-14, BR-15, error)
    Given the installer directory "/home/kbot/dev/installer" <install>
    And the storage holds the bundle "ev-basic-2025.03.0020" version "2025.03.0020" pinning:
      | product       | commit     | branch              |
      | kbot          | c0ffee2503 | release-2025.03-dev |
      | site-konverso | c0ffee2501 | release-2025.03-dev |
    When the operator runs "kbot-installer upgrade <options> -y"
    Then the error output contains "Installer is not ready for the upgrade:"
    And the error output contains "<problem>"
    And nothing is downloaded
    And no process is run
    And the exit code is 1

    Examples:
      | rule  | install                                                     | options                         | problem                                                                     |
      | BR-10 | was installed from bundle "ev-basic" version "2025.03.0010" | -v 2027.01                      | No bundle 'ev-basic' 2027.01.* found in storage                             |
      | BR-11 | was installed from bundle "ev-basic" version "2025.03.0010" | -b ev-basic-2026.01.9999        | Bundle 'ev-basic-2026.01.9999' was not found in storage                     |
      | BR-12 | was installed from bundle "ev-basic" version "2025.03.0010" | -b ev-basic-2025.03.0020        | Bundle ev-basic-2025.03.0020 is not newer than the installed ev-basic       |
      | BR-13 | was not installed from a bundle                             | -p unknown -v 2026.01           | Product 'unknown' is not installed in '/home/kbot/dev/installer'            |
      | BR-14 | was not installed from a bundle                             | -p site-konverso -v 2025.03     | 'site-konverso' is at version 2025.03: 2025.03 is not newer                 |
      | BR-15 | was not installed from a bundle                             | -p site-konverso -v abc         | Invalid version 'abc'                                                       |

  @since-2026.01 @AC-KBOT-INST-04-08 @BR-16 @BR-18 @BR-24
  Scenario: Local builds and dirty working copies are all reported and nothing changes (BR-16, BR-18, BR-24, error)
    Given the product "ai-tools" in "/home/kbot/dev/installer" is a local build
    And the product "demo" in "/home/kbot/dev/installer" is a git working copy on branch "release-2025.03-dev"
    And the git working copy "/home/kbot/dev/installer/demo" has uncommitted changes in "description.xml"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 -y"
    Then the error output contains "Installer is not ready for the upgrade:"
    And the error output contains "ai-tools: local build cannot be upgraded (only storage downloads and git working copies can; use --force to keep it as is)"
    And the error output contains "demo: Uncommitted changes: description.xml"
    And nothing is downloaded
    And no process is run
    And the database is not contacted
    And the file "/home/kbot/dev/installer/site-konverso/description.json" contains "c0ffee2501"
    And the file "/home/kbot/dev/work/var/products.json" contains "[]"
    And the git working copy "/home/kbot/dev/installer/demo" is on branch "release-2025.03-dev"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-04-09 @BR-17 @BR-34
  Scenario: --force keeps symlinked and locally built products (BR-17, BR-34)
    Given the product "ai-tools" in "/home/kbot/dev/installer" is a local build
    And the directory "/home/kbot/dev/git/ai-assets" exists
    And the file "/home/kbot/dev/git/ai-assets/description.xml" contains "<product name='ai-assets' type='solution'/>"
    And "/home/kbot/dev/installer/ai-assets" is a symlink to "/home/kbot/dev/git/ai-assets"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 -B KB-12345 --force -y"
    Then the output contains "ai-tools: local build kept as is (--force)"
    And the output contains "ai-assets: local symlink kept as is (--force)"
    And the file "/home/kbot/dev/installer/ai-tools/description.xml" contains "ai-tools"
    And "/home/kbot/dev/installer/ai-assets" is a symlink to "/home/kbot/dev/git/ai-assets"
    And the output does not contain "Removed products:"
    And the warning "Keeping local build ai-tools, no longer needed by the target" is logged
    And the output ends with "Upgrade completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-10 @BR-19 @BR-20
  Scenario Outline: Git working copies move to the first branch they have (BR-19, BR-20)
    Given the storage holds the product "site-konverso" version "2026.01" at commit "c0ffee0001" of branch "release-2026.01-dev" with parents "kbot, demo"
    And the git provider "github" serves the product "demo" on the branches "<branches>"
    And the product "demo" in "/home/kbot/dev/installer" is a git working copy of the git provider "github" on branch "release-2025.03-dev"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 -B KB-12345 -y"
    Then the git working copy "/home/kbot/dev/installer/demo" is on branch "<chosen>" at the head of origin
    And the output <note>
    And the exit code is 0

    Examples:
      | rule  | branches                                                   | chosen              | note                                                                                     |
      | BR-19 | release-2025.03-dev, KB-12345, release-2026.01-dev, master | KB-12345            | does not contain "demo: branch"                                                          |
      | BR-20 | release-2025.03-dev, release-2026.01-dev, master           | release-2026.01-dev | contains "demo: branch 'KB-12345' not found, using branch 'release-2026.01-dev'"         |
      | BR-20 | main, release-2025.03-dev                                  | main                | contains "demo: branch 'KB-12345' not found, using default branch 'main'"                |

  @since-2026.01 @AC-KBOT-INST-04-11 @BR-21
  Scenario: A working copy without any candidate branch cancels the upgrade (BR-21, error)
    Given the git provider "github" serves the product "demo" on the branches "release-2025.03-dev"
    And the product "demo" in "/home/kbot/dev/installer" is a git working copy of the git provider "github" on branch "release-2025.03-dev"
    And the git working copy "/home/kbot/dev/installer/demo" records no default branch for origin
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 -y"
    Then the error output contains "Installer is not ready for the upgrade:"
    And the error output contains "demo: none of the branches 'release-2026.01-dev', 'master' found locally or on origin"
    And nothing is downloaded
    And no process is run
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-04-12 @BR-22
  Scenario: A local-only branch is checked out without pull (BR-22)
    Given the storage holds the product "site-konverso" version "2026.01" at commit "c0ffee0001" of branch "release-2026.01-dev" with parents "kbot, demo"
    And the git provider "github" serves the product "demo" on the branches "release-2025.03-dev"
    And the product "demo" in "/home/kbot/dev/installer" is a git working copy of the git provider "github" on branch "release-2025.03-dev"
    And the git working copy "/home/kbot/dev/installer/demo" has the local branch "release-2026.01-dev" that origin does not have
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 -y"
    Then the output contains "demo: branch 'release-2026.01-dev' is not on origin, it will not be pulled"
    And the git working copy "/home/kbot/dev/installer/demo" is on branch "release-2026.01-dev"
    And the git working copy "/home/kbot/dev/installer/demo" is not pulled
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-13 @BR-23 @BR-34 @BR-35
  Scenario: Products dropped by the new bundle are removed (BR-23, BR-34, BR-35)
    Given the installer directory "/home/kbot/dev/installer" was installed from bundle "ev-basic" version "2025.03.0010"
    And the product "old-solution" in "/home/kbot/dev/installer" is a git working copy on branch "release-2025.03-dev"
    And the storage holds the bundle "ev-basic-2026.01.0003" version "2026.01.0003" pinning:
      | product       | commit     | branch              |
      | kbot          | c0ffee0003 | release-2026.01-dev |
      | site-konverso | c0ffee0001 | release-2026.01-dev |
    When the operator runs "kbot-installer upgrade -b ev-basic-2026.01.0003 -y"
    Then "/home/kbot/dev/installer/old-solution" no longer exists
    And the git working copy "/home/kbot/dev/installer/.removed_<timestamp>/old-solution" is on branch "release-2025.03-dev"
    And the output contains "Removed products: old-solution"
    And the output contains "Removed git working copies moved to '/home/kbot/dev/installer/.removed_"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-14 @BR-25
  Scenario: Declining the confirmation changes nothing (BR-25, error)
    Given the operator will answer "n" to "Continue with upgrade?"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01"
    Then the question "Continue with upgrade?" is asked
    And the output contains "Aborted!"
    And no process is run
    And nothing is downloaded
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-04-15 @BR-26 @BR-27 @BR-31
  Scenario: -y backs up to the default file without asking (BR-26, BR-27, BR-31)
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 -y"
    Then no question is asked
    And the database is dumped to "/home/kbot/dev/installer/backup_<YYYYMMDD_HHMMSS>.sql"
    And the output contains "Backing up database to '/home/kbot/dev/installer/backup_"
    And the command ran, in order:
      | command                                                               |
      | /home/kbot/dev/work/bin/pg.sh start                                   |
      | /home/kbot/dev/work/bin/dump_db.sh -f /home/kbot/dev/installer/backup_ |
      | /home/kbot/dev/work/bin/kbot.sh stop                                  |
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-16 @BR-28 @BR-29 @BR-30
  Scenario Outline: The backup file is chosen interactively or by option (BR-28, BR-29, BR-30)
    Given the operator will answer "y" to "Continue with upgrade?"
    And the operator will answer "<backup>" to "Back up the database before upgrading?"
    And the operator will answer "" to "Backup file"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 <options>"
    Then the question "Back up the database before upgrading?" <asked>
    And <dump>
    And the exit code is 0

    Examples:
      | rule  | options                          | backup | asked        | dump                                                                                    |
      | BR-28 |                                  | y      | is asked     | the database is dumped to "/home/kbot/dev/installer/backup_<YYYYMMDD_HHMMSS>.sql"       |
      | BR-29 |                                  | n      | is asked     | the command did not run "dump_db.sh"                                                    |
      | BR-29 | --no-backup                      |        | is not asked | the command did not run "dump_db.sh"                                                    |
      | BR-30 | --backup-file ~/backups/kbot.sql |        | is not asked | the database is dumped to "/home/kbot/backups/kbot.sql"                                 |

  @since-2026.01 @AC-KBOT-INST-04-17 @BR-32
  Scenario: A Kbot stop failure is only a warning (BR-32)
    Given the program "kbot.sh stop" exits with code 1
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 -y"
    Then the error output contains "Warning: '/home/kbot/dev/work/bin/kbot.sh stop' failed (exit 1)."
    And the command ran, in order:
      | command                                  |
      | /home/kbot/dev/work/bin/kbot.sh stop     |
      | /home/kbot/dev/work/bin/upgrade_db.sh    |
      | /home/kbot/dev/work/bin/kbot.sh restart  |
    And the output ends with "Upgrade completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-18 @BR-33
  Scenario: Storage products are downloaded again with the chosen storage and provider (BR-33)
    Given the file "/home/kbot/dev/installer/kbot/stale.txt" contains "2025.03"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 --storage s3 --provider github --provider storage -y"
    Then "/home/kbot/dev/installer/kbot/stale.txt" no longer exists
    And the git providers are tried in order:
      | provider |
      | github   |
    And the product "site-konverso" is downloaded from the "artifacts" area of the "s3" storage
    And the product "kbot" is downloaded from the "artifacts" area of the "s3" storage
    And the file "/home/kbot/dev/installer/kbot/description.json" contains "release-2026.01-dev"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-19 @BR-36 @BR-37
  Scenario: The workarea is relinked without prompt and the requirements installed (BR-36, BR-37)
    Given the workarea "/home/kbot/dev/work" holds the broken symlink "conf/gone.conf"
    And the storage archive of "kbot" on branch "release-2026.01-dev" holds the file "bin/pip3.sh" containing "#!/bin/sh"
    And the storage archive of "site-konverso" on branch "release-2026.01-dev" holds the file "requirements.txt" containing "requests"
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.13" and PostgreSQL "16.10"
    And the operator will answer "y" to "Continue with upgrade?"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 --backup-file /tmp/b.sql"
    Then the only question asked is "Continue with upgrade?"
    And "/home/kbot/dev/work/conf/gone.conf" no longer exists
    And "/home/kbot/dev/work/bin/pip3.sh" is a symlink to "/home/kbot/dev/installer/kbot/bin/pip3.sh"
    And the command ran, in order:
      | command                                                                                                    |
      | /home/kbot/dev/installer/kbot/bin/pip3.sh install -r /home/kbot/dev/installer/site-konverso/requirements.txt |
      | /home/kbot/dev/work/bin/upgrade_db.sh                                                                      |
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-20 @BR-37
  Scenario: --skip-python-requirements skips the requirements (BR-37)
    Given the storage archive of "kbot" on branch "release-2026.01-dev" holds the file "bin/pip3.sh" containing "#!/bin/sh"
    And the storage archive of "site-konverso" on branch "release-2026.01-dev" holds the file "requirements.txt" containing "requests"
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.13" and PostgreSQL "16.10"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 --skip-python-requirements -y"
    Then the command did not run "pip3.sh"
    And the command ran "/home/kbot/dev/work/bin/upgrade_db.sh"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-21 @BR-38 @BR-39
  Scenario: A PostgreSQL major change rebuilds the database from the backup (BR-38, BR-39)
    Given a kbot workarea exists in "/home/kbot/dev/work" with an internal database of PostgreSQL 14
    And the database "kbot_db" has tables
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.13" and PostgreSQL "16.10"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 --db-user kbot_db_user --db-name kbot_db -y"
    Then the output contains "PostgreSQL 14 -> 16.10: rebuilding the database from '/home/kbot/dev/installer/backup_"
    And a directory matching "/home/kbot/dev/work/var/db_pg14_<timestamp>" exists
    And the file "/home/kbot/dev/work/var/db/PG_VERSION" contains "16"
    And the database "kbot_db" exists, owned by "kbot_db_user"
    And the database "kbot_db" has the table "existing_data"
    And the command ran, in order:
      | command                                                                                                                                                            |
      | /home/kbot/dev/work/bin/dump_db.sh -f /home/kbot/dev/installer/backup_                                                                                             |
      | /home/kbot/dev/work/bin/kbot.sh stop                                                                                                                               |
      | /home/kbot/dev/installer/3rdparty/postgresql-16.10/bin/pg_ctl -D /home/kbot/dev/work/var/db -o -E UTF8                                                             |
      | /home/kbot/dev/installer/3rdparty/postgresql-16.10/bin/pg_ctl start -l /home/kbot/dev/work/logs/postgres.log -D /home/kbot/dev/work/var/db --silent -w -o -p5432  |
      | /home/kbot/dev/installer/3rdparty/postgresql-16.10/bin/psql -v ON_ERROR_STOP=1 -q -h localhost -p 5432 -U kbot_db_user -d kbot_db -f /home/kbot/dev/installer/backup_ |
      | /home/kbot/dev/installer/3rdparty/postgresql-16.10/bin/pg_ctl -D /home/kbot/dev/work/var/db --silent stop                                                          |
      | /home/kbot/dev/work/bin/upgrade_db.sh                                                                                                                              |
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-22 @BR-40
  Scenario: The database is kept when the PostgreSQL major is unchanged (BR-40)
    Given a kbot workarea exists in "/home/kbot/dev/work" with an internal database of PostgreSQL 16
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.13" and PostgreSQL "16.10"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 -y"
    Then no directory matches "/home/kbot/dev/work/var/db_pg<anything>"
    And the file "/home/kbot/dev/work/var/db/PG_VERSION" contains "16"
    And the command did not run "pg_ctl"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-23 @BR-41 @BR-45
  Scenario: A PostgreSQL major change without backup fails (BR-41, BR-45, error)
    Given a kbot workarea exists in "/home/kbot/dev/work" with an internal database of PostgreSQL 14
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.13" and PostgreSQL "16.10"
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 --no-backup -y"
    Then the error output contains "Error upgrading: '/home/kbot/dev/work/var/db' was created by PostgreSQL 14, which PostgreSQL 16.10 cannot start, and '--no-backup' was given: there is no backup to rebuild it from."
    And the output does not contain "The database backup is"
    And the command did not run "upgrade_db.sh"
    And the file "/home/kbot/dev/work/var/db/PG_VERSION" contains "14"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-04-24 @BR-42 @BR-43 @BR-44
  Scenario: Database upgrade, load, learn and restart (BR-42, BR-43, BR-44)
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 --with-learn -y"
    Then the command ran, in order:
      | command                                    |
      | /home/kbot/dev/work/bin/kbot.sh stop       |
      | /home/kbot/dev/work/bin/pg.sh start        |
      | /home/kbot/dev/work/bin/redis.sh start     |
      | /home/kbot/dev/work/bin/upgrade_db.sh      |
      | /home/kbot/dev/work/bin/upgrade_patch.sh   |
      | /home/kbot/dev/work/bin/kbot.sh load       |
      | /home/kbot/dev/work/bin/kbot.sh learn      |
      | /home/kbot/dev/work/bin/kbot.sh restart    |
    And the output ends with "Upgrade completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-04-25 @BR-45
  Scenario: A failing step reports the backup to restore (BR-45, error)
    Given the program "upgrade_db.sh" exits with code 1
    When the operator runs "kbot-installer upgrade -p site-konverso -v 2026.01 --backup-file /tmp/b.sql -y"
    Then the error output contains "Error upgrading: '/home/kbot/dev/work/bin/upgrade_db.sh' failed (exit 1)."
    And the error output contains "The database backup is '/tmp/b.sql' (restore it with 'bin/restore_db.sh')."
    And no command starting with "/home/kbot/dev/work/bin/kbot.sh restart" ran
    And the exit code is 1
