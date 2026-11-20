# language: en
Feature: KBOT-INST-06 Admin password

  @since-2026.01 @AC-KBOT-INST-06-01 @BR-01 @BR-02 @BR-09 @BR-10 @BR-11 @BR-16
  Scenario: Set the admin password from the environment on the internal database (nominal case) (BR-01, BR-02, BR-09, BR-10, BR-11, BR-16)
    Given the environment variable PG_DIR is "/opt/pgsql"
    And the database "kbot_db" on "localhost" port 5432 accepts the user "kbot_db_user" with the password "kbot_db_pwd"
    And the database "kbot_db" contains the kbot users "admin, jdoe"
    And the environment variable KBOT_ADMIN_PASSWORD is "S3cret!"
    When the operator runs "kbot-installer set-admin-password"
    Then the password of "admin" in "kbot_db" is stored as a salted hash, not as "S3cret!"
    And the password of "admin" in "kbot_db" verifies "S3cret!"
    And the password of "jdoe" in "kbot_db" is unchanged
    And the output is:
      """
      Admin password set successfully.
      """
    And the output does not contain "S3cret!"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-06-02 @BR-10
  Scenario: Set the admin password on an external database (BR-10)
    Given the environment variable PG_DIR is "/opt/pgsql"
    And the database "custom_db" on "db.example.com" port 6543 accepts the user "custom_user" with the password "custom_pwd"
    And the database "custom_db" contains the kbot users "admin"
    And the environment variable KBOT_ADMIN_PASSWORD is "S3cret!"
    When the operator runs "kbot-installer set-admin-password --db-host db.example.com --db-port 6543 --db-user custom_user --db-password custom_pwd --db-name custom_db"
    Then the password of "admin" in "custom_db" verifies "S3cret!"
    And the output is:
      """
      Admin password set successfully.
      """
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-06-03 @BR-03 @BR-07 @BR-08
  Scenario: Generate a random admin password (BR-03, BR-07, BR-08)
    Given the environment variable PG_DIR is "/opt/pgsql"
    And the database "kbot_db" on "localhost" port 5432 accepts the user "kbot_db_user" with the password "kbot_db_pwd"
    And the database "kbot_db" contains the kbot users "admin"
    And the environment variable KBOT_ADMIN_PASSWORD is not set
    When the operator runs "kbot-installer set-admin-password --no-admin-password"
    Then the output contains "Generated kbot admin password: " followed by 22 URL-safe characters
    And the password of "admin" in "kbot_db" verifies the password printed after "Generated kbot admin password: "
    And the output ends with "Admin password set successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-06-04 @BR-04 @BR-08
  Scenario: The environment password wins over the generation flag (BR-04, BR-08)
    Given the environment variable PG_DIR is "/opt/pgsql"
    And the database "kbot_db" on "localhost" port 5432 accepts the user "kbot_db_user" with the password "kbot_db_pwd"
    And the database "kbot_db" contains the kbot users "admin"
    And the environment variable KBOT_ADMIN_PASSWORD is "S3cret!"
    When the operator runs "kbot-installer set-admin-password --no-admin-password"
    Then the password of "admin" in "kbot_db" verifies "S3cret!"
    And the output does not contain "Generated kbot admin password"
    And the output does not contain "S3cret!"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-06-05 @BR-05 @BR-06
  Scenario Outline: The admin password is missing (BR-05, BR-06, error)
    Given the environment variable PG_DIR is "/opt/pgsql"
    And the environment variable KBOT_ADMIN_PASSWORD <state>
    When the operator runs "kbot-installer set-admin-password"
    Then the error output contains "Error: Admin password required: set 'KBOT_ADMIN_PASSWORD' or use '--no-admin-password'."
    And the database is not contacted
    And the exit code is 2

    Examples:
      | state      | rule  |
      | is not set | BR-06 |
      | is empty   | BR-05 |

  @since-2026.01 @AC-KBOT-INST-06-06 @BR-12
  Scenario: PostgreSQL cannot be located (BR-12, error)
    Given the environment variable PG_DIR is not set
    And the directory "/home/kbot/installer/3rdparty" does not exist
    And the database "kbot_db" on "db.example.com" port 5432 accepts the user "kbot_db_user" with the password "kbot_db_pwd"
    And the database "kbot_db" contains the kbot users "admin"
    And the environment variable KBOT_ADMIN_PASSWORD is "S3cret!"
    When the operator runs "kbot-installer set-admin-password -i /home/kbot/installer --db-host db.example.com"
    Then the error output contains "Error: Unable to locate PostgreSQL: set the 'PG_DIR' environment variable, or ensure '/home/kbot/installer/3rdparty/versions.env' exists and defines 'PG_DIR'."
    And the password of "admin" in "kbot_db" is unchanged
    And the database is not contacted
    And the exit code is 2

  @since-2026.01 @AC-KBOT-INST-06-07 @BR-13
  Scenario: PG_DIR from the environment is used before the installer directory (BR-13)
    Given the environment variable PG_DIR is "/opt/pgsql"
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.13" and PostgreSQL "16.4"
    And the database "kbot_db" on "localhost" port 5432 accepts the user "kbot_db_user" with the password "kbot_db_pwd"
    And the database "kbot_db" contains the kbot users "admin"
    And the environment variable KBOT_ADMIN_PASSWORD is "S3cret!"
    When the operator runs "kbot-installer set-admin-password"
    Then PostgreSQL is located in "/opt/pgsql"
    And the output is:
      """
      Admin password set successfully.
      """
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-06-08 @BR-14
  Scenario: The database has no admin account (BR-14, error)
    Given the environment variable PG_DIR is "/opt/pgsql"
    And the database "kbot_db" on "localhost" port 5432 accepts the user "kbot_db_user" with the password "kbot_db_pwd"
    And the database "kbot_db" contains the kbot users "jdoe"
    And the environment variable KBOT_ADMIN_PASSWORD is "S3cret!"
    When the operator runs "kbot-installer set-admin-password"
    Then the error output contains "Error setting admin password: No 'admin' account found in the database: the users load (users.conf) did not create it."
    And the kbot users of "kbot_db" are unchanged
    And the output does not contain "Admin password set successfully."
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-06-09 @BR-15
  Scenario: The database cannot be reached (BR-15, error)
    Given the environment variable PG_DIR is "/opt/pgsql"
    And the internal PostgreSQL server of "/home/kbot/dev/work" holds the database "kbot_db" and is stopped
    And the database "kbot_db" contains the kbot users "admin"
    And the environment variable KBOT_ADMIN_PASSWORD is "S3cret!"
    When the operator runs "kbot-installer set-admin-password"
    Then the error output contains "Error setting admin password: connection to server at"
    And the error output contains "port 5432 failed: Connection refused"
    And the internal PostgreSQL server of "/home/kbot/dev/work" is stopped
    And the command did not run "pg_ctl"
    And the password of "admin" in "kbot_db" is unchanged
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-06-10 @BR-17
  Scenario: The standalone command behaves like the kbot-installer subcommand (BR-17)
    Given the environment variable PG_DIR is "/opt/pgsql"
    And the database "kbot_db" on "localhost" port 5432 accepts the user "kbot_db_user" with the password "kbot_db_pwd"
    And the database "kbot_db" contains the kbot users "admin"
    And the environment variable KBOT_ADMIN_PASSWORD is "S3cret!"
    When the operator runs "kbot-set-admin-password"
    Then the password of "admin" in "kbot_db" verifies "S3cret!"
    And the output is:
      """
      Admin password set successfully.
      """
    And the exit code is 0
