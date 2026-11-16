# language: en
Feature: KBOT-INST-07 Uninstallation

  Background:
    Given the environment variable PG_DIR is "/opt/pgsql"

  @since-2026.01 @AC-KBOT-INST-07-01 @BR-04 @BR-08 @BR-09 @BR-19 @BR-21 @BR-25
  Scenario: Uninstall a workarea with its internal database (nominal case) (BR-04, BR-08, BR-09, BR-19, BR-21, BR-25)
    Given a kbot workarea exists in "/home/kbot/work" with an internal database of PostgreSQL 16
    And the internal database of "/home/kbot/work" holds the database "kbot_db" owned by "kbot_db_user" with the password "kbot_db_pwd"
    And the internal PostgreSQL server of "/home/kbot/work" is running on port 5432
    And the operator will answer "y" to "Continue with uninstallation? [y/N]"
    When the operator runs "kbot-installer uninstall -w /home/kbot/work"
    Then the output contains, in order:
      | line                                                                                            |
      | About to remove the workarea '/home/kbot/work' entirely, including all its configuration files, |
      | and the internal database under '/home/kbot/work/var/db'.                                       |
      | The database will NOT be backed up (use --backup-file to keep a dump).                          |
      | Continue with uninstallation? [y/N]                                                             |
      | Stopping kbot services...                                                                       |
      | Removing database...                                                                            |
      | Removing workarea directory '/home/kbot/work'...                                                |
    And the question "Continue with uninstallation? [y/N]" is asked
    And the command ran, in order:
      | command                                                |
      | /home/kbot/work/bin/kbot.sh stop                       |
      | /opt/pgsql/bin/pg_ctl -D /home/kbot/work/var/db --silent stop |
    And the command did not run "pg_dump"
    And the internal PostgreSQL server of "/home/kbot/work" is stopped
    And "/home/kbot/work/var/db" no longer exists
    And "/home/kbot/work" no longer exists
    And the output ends with "Uninstallation completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-07-02 @BR-01 @BR-14 @BR-26
  Scenario: Uninstall the default workarea with the default database settings (BR-01, BR-14, BR-26)
    Given the operator's home directory is "/home/kbot"
    And the environment variable PG_DIR is not set
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.13" and PostgreSQL "16.4"
    And the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And a kbot workarea exists in "/home/kbot/dev/work" with an internal database of PostgreSQL 16
    And the internal database of "/home/kbot/dev/work" holds the database "kbot_db" owned by "kbot_db_user" with the password "kbot_db_pwd"
    And the internal PostgreSQL server of "/home/kbot/dev/work" is running on port 5432
    When the operator runs "kbot-installer uninstall -y --backup-file /home/kbot/kbot.sql"
    Then the command ran "/home/kbot/dev/installer/3rdparty/postgresql-16.4/bin/pg_dump -h localhost -p 5432 -U kbot_db_user --no-privileges --no-owner -n public -f /home/kbot/kbot.sql kbot_db"
    And the command ran "/home/kbot/dev/installer/3rdparty/postgresql-16.4/bin/pg_ctl -D /home/kbot/dev/work/var/db --silent stop"
    And the command ran "/home/kbot/dev/work/bin/kbot.sh stop"
    And "/home/kbot/dev/work" no longer exists
    And the file "/home/kbot/dev/installer/kbot/description.xml" contains "kbot"
    And the file "/home/kbot/dev/installer/3rdparty/versions.env" contains "PG_DIR"
    And the output ends with "Uninstallation completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-07-03 @BR-03
  Scenario Outline: Both workarea layouts are accepted (BR-03)
    Given the <marker>
    When the operator runs "kbot-installer uninstall -w /home/kbot/work -y"
    Then "/home/kbot/work" no longer exists
    And the output ends with "Uninstallation completed successfully."
    And the exit code is 0

    Examples:
      | marker                                                   | rule  |
      | directory "/home/kbot/work/products/kbot" exists         | BR-03 |
      | file "/home/kbot/work/var/products.json" contains "[]"   | BR-03 |

  @since-2026.01 @AC-KBOT-INST-07-04 @BR-02
  Scenario: A directory that is not a kbot workarea is refused (BR-02, error)
    Given the file "/home/kbot/docs/notes.txt" contains "my notes"
    When the operator runs "kbot-installer uninstall -w /home/kbot/docs -y"
    Then the error output contains "Error: '/home/kbot/docs' is not a kbot workarea directory (no 'products/kbot' nor 'var/products.json')."
    And the file "/home/kbot/docs/notes.txt" contains "my notes"
    And the command did not run "kbot.sh"
    And the command did not run "pg_ctl"
    And the database is not contacted
    And the exit code is 2

  @since-2026.01 @AC-KBOT-INST-07-05 @BR-11
  Scenario: The operator declines the confirmation (BR-11, error)
    Given a kbot workarea exists in "/home/kbot/work" with an internal database of PostgreSQL 16
    And the internal database of "/home/kbot/work" holds the database "kbot_db" owned by "kbot_db_user" with the password "kbot_db_pwd"
    And the database "kbot_db" has tables
    And the internal PostgreSQL server of "/home/kbot/work" is running on port 5432
    And the operator will answer "n" to "Continue with uninstallation? [y/N]"
    When the operator runs "kbot-installer uninstall -w /home/kbot/work"
    Then the question "Continue with uninstallation? [y/N]" is asked
    And the error output contains "Aborted!"
    And the command did not run "kbot.sh"
    And the command did not run "pg_ctl"
    And the file "/home/kbot/work/var/products.json" contains "[]"
    And the file "/home/kbot/work/var/db/PG_VERSION" contains "16"
    And the internal PostgreSQL server of "/home/kbot/work" is running on port 5432
    And the database "kbot_db" has the table "existing_data"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-07-06 @BR-08 @BR-12
  Scenario: The confirmation is skipped with --yes (BR-08, BR-12)
    Given a kbot workarea exists in "/home/kbot/work" with an internal database of PostgreSQL 16
    When the operator runs "kbot-installer uninstall -w /home/kbot/work --yes"
    Then the output contains "About to remove the workarea '/home/kbot/work' entirely, including all its configuration files,"
    And no question is asked
    And "/home/kbot/work" no longer exists
    And the output ends with "Uninstallation completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-07-07 @BR-05 @BR-06 @BR-15
  Scenario Outline: The database is backed up before the removal (BR-05, BR-06, BR-15)
    Given a kbot workarea exists in "/home/kbot/work" with an internal database of PostgreSQL 16
    And the internal database of "/home/kbot/work" holds the database "kbot_db" owned by "kbot_db_user" with the password "kbot_db_pwd"
    And the database "kbot_db" has tables
    And the internal PostgreSQL server of "/home/kbot/work" is running on port 5432
    And the directory "/home/kbot/backups" exists
    And the local date and time is "2026-11-09 14:30:05"
    When the operator runs "kbot-installer uninstall -w /home/kbot/work --backup-file <backup> -y"
    Then the output contains "The database will first be backed up to '<file>'."
    And the output contains, in order:
      | line                                |
      | Backing up database to '<file>'...  |
      | Stopping kbot services...           |
    And the command ran, in order:
      | command                                                                                                       |
      | /opt/pgsql/bin/pg_dump -h localhost -p 5432 -U kbot_db_user --no-privileges --no-owner -n public -f <file> kbot_db |
      | /home/kbot/work/bin/kbot.sh stop                                                                              |
    And the file "<file>" contains "CREATE TABLE existing_data"
    And "/home/kbot/work" no longer exists
    And the exit code is 0

    Examples:
      | backup                      | file                                        | rule  |
      | /home/kbot/backups/kbot.sql | /home/kbot/backups/kbot.sql                 | BR-05 |
      | /home/kbot/new/kbot.sql     | /home/kbot/new/kbot.sql                     | BR-05 |
      | ~/backups/kbot.sql          | /home/kbot/backups/kbot.sql                 | BR-05 |
      | /home/kbot/backups          | /home/kbot/backups/dump_20261109_143005.sql | BR-06 |

  @since-2026.01 @AC-KBOT-INST-07-08 @BR-07
  Scenario: A backup file inside the workarea is refused (BR-07, error)
    Given a kbot workarea exists in "/home/kbot/work" with an internal database of PostgreSQL 16
    When the operator runs "kbot-installer uninstall -w /home/kbot/work --backup-file /home/kbot/work/var/kbot.sql -y"
    Then the error output contains "Error: Backup file '/home/kbot/work/var/kbot.sql' must be outside the workarea '/home/kbot/work', which is removed."
    And the output does not contain "About to remove the workarea"
    And no question is asked
    And the command did not run "kbot.sh"
    And the command did not run "pg_ctl"
    And the file "/home/kbot/work/var/products.json" contains "[]"
    And the file "/home/kbot/work/var/db/PG_VERSION" contains "16"
    And the exit code is 2

  @since-2026.01 @AC-KBOT-INST-07-09 @BR-16
  Scenario: A stopped internal database is started to be backed up (BR-16)
    Given a kbot workarea exists in "/home/kbot/work" with an internal database of PostgreSQL 16
    And the internal database of "/home/kbot/work" holds the database "kbot_db" owned by "kbot_db_user" with the password "kbot_db_pwd"
    And the database "kbot_db" has tables
    And the internal PostgreSQL server of "/home/kbot/work" is stopped
    When the operator runs "kbot-installer uninstall -w /home/kbot/work --backup-file /home/kbot/backups/kbot.sql -y"
    Then the command ran, in order:
      | command                                                          |
      | /opt/pgsql/bin/pg_ctl start -l /home/kbot/work/logs/postgres.log -D /home/kbot/work/var/db |
      | /opt/pgsql/bin/pg_dump -h localhost -p 5432                      |
    And the file "/home/kbot/backups/kbot.sql" contains "CREATE TABLE existing_data"
    And the output ends with "Uninstallation completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-07-10 @BR-17
  Scenario: A workarea without database is still uninstalled (BR-17)
    Given a kbot workarea exists in "/home/kbot/work"
    And the directory "/home/kbot/work/var/db" does not exist
    When the operator runs "kbot-installer uninstall -w /home/kbot/work --backup-file /home/kbot/backups -y"
    Then the error output contains "Warning: no database found, nothing to back up."
    And the command did not run "pg_dump"
    And "/home/kbot/work" no longer exists
    And the output ends with "Uninstallation completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-07-11 @BR-18
  Scenario: Nothing is removed when the backup fails (BR-18, error)
    Given a kbot workarea exists in "/home/kbot/work" with an internal database of PostgreSQL 16
    And the internal database of "/home/kbot/work" holds the database "kbot_db" owned by "kbot_db_user" with the password "kbot_db_pwd"
    And the database "kbot_db" has tables
    And the internal PostgreSQL server of "/home/kbot/work" is running on port 5432
    And the program "pg_dump" fails with "pg_dump: error: permission denied for table existing_data"
    When the operator runs "kbot-installer uninstall -w /home/kbot/work --backup-file /home/kbot/backups/kbot.sql -y"
    Then the error output contains "Error uninstalling workarea: Failed to dump database 'kbot_db' to /home/kbot/backups/kbot.sql: pg_dump: error: permission denied for table existing_data"
    And the output does not contain "Stopping kbot services..."
    And the command did not run "kbot.sh"
    And the file "/home/kbot/work/var/products.json" contains "[]"
    And the file "/home/kbot/work/var/db/PG_VERSION" contains "16"
    And the internal PostgreSQL server of "/home/kbot/work" is running on port 5432
    And the database "kbot_db" has the table "existing_data"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-07-12 @BR-10 @BR-23
  Scenario: Uninstall a workarea that uses an external database (BR-10, BR-23)
    Given a kbot workarea exists in "/home/kbot/work"
    And the database "kbot_db" on "db.example.com" port 5432 accepts the user "kbot_db_user" with the password "secret"
    And the database "kbot_db" has tables
    When the operator runs "kbot-installer uninstall -w /home/kbot/work --db-host db.example.com --db-password secret -y"
    Then the output contains "and all objects owned by 'kbot_db_user' in the external database 'kbot_db' on 'db.example.com'."
    And the objects owned by "kbot_db_user" in "kbot_db" are dropped
    And the database "kbot_db" exists, owned by "kbot_db_user"
    And the user "kbot_db_user" on "db.example.com" port 5432 has the password "secret"
    And the command did not run "pg_ctl"
    And "/home/kbot/work" no longer exists
    And the output ends with "Uninstallation completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-07-13 @BR-13
  Scenario: PostgreSQL cannot be located (BR-13, error)
    Given the environment variable PG_DIR is not set
    And the directory "/home/kbot/installer/3rdparty" does not exist
    And a kbot workarea exists in "/home/kbot/work"
    When the operator runs "kbot-installer uninstall -i /home/kbot/installer -w /home/kbot/work -y"
    Then the error output contains "Error: Unable to locate PostgreSQL: set the 'PG_DIR' environment variable, or ensure '/home/kbot/installer/3rdparty/versions.env' exists and defines 'PG_DIR'."
    And the command did not run "kbot.sh"
    And the file "/home/kbot/work/var/products.json" contains "[]"
    And the exit code is 2

  @since-2026.01 @AC-KBOT-INST-07-14 @BR-20
  Scenario: A failing Kbot stop does not block the uninstallation (BR-20)
    Given a kbot workarea exists in "/home/kbot/work" with an internal database of PostgreSQL 16
    And the internal PostgreSQL server of "/home/kbot/work" is running on port 5432
    And the program "kbot.sh stop" exits with code 1
    When the operator runs "kbot-installer uninstall -w /home/kbot/work -y"
    Then the error output contains "Warning: '/home/kbot/work/bin/kbot.sh stop' failed (exit 1)."
    And the command ran "/opt/pgsql/bin/pg_ctl -D /home/kbot/work/var/db --silent stop"
    And "/home/kbot/work/var/db" no longer exists
    And the output ends with "Uninstallation completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-07-15 @BR-22
  Scenario: The internal PostgreSQL server does not stop (BR-22, error)
    Given a kbot workarea exists in "/home/kbot/work" with an internal database of PostgreSQL 16
    And the internal PostgreSQL server of "/home/kbot/work" is running on port 5432
    And the internal PostgreSQL server of "/home/kbot/work" keeps running after "pg_ctl stop"
    When the operator runs "kbot-installer uninstall -w /home/kbot/work -y"
    Then the error output contains "Error uninstalling workarea: PostgreSQL server for '/home/kbot/work/var/db' is still running after 'pg_ctl stop'."
    And the output does not contain "Removing workarea directory"
    And the file "/home/kbot/work/var/products.json" contains "[]"
    And the file "/home/kbot/work/var/db/PG_VERSION" contains "16"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-07-16 @BR-24
  Scenario: The external database cannot be reached (BR-24, error)
    Given a kbot workarea exists in "/home/kbot/work"
    And the database server "db.example.com" port 5432 is unreachable
    When the operator runs "kbot-installer uninstall -w /home/kbot/work --db-host db.example.com -y"
    Then the error output contains "Error uninstalling workarea: connection to server at "
    And the error output contains "port 5432 failed: Connection refused"
    And the output does not contain "Removing workarea directory"
    And the file "/home/kbot/work/var/products.json" contains "[]"
    And the exit code is 1
