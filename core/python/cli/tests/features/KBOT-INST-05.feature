# language: en
Feature: KBOT-INST-05 Database objects loading and training

  @since-2026.01 @AC-KBOT-INST-05-01 @BR-01 @BR-02 @BR-03 @BR-09 @BR-10
  Scenario: Load every object into the default workarea (nominal case) (BR-01, BR-02, BR-03, BR-09, BR-10)
    Given the operator's home directory is "/home/kbot"
    And a kbot workarea exists in "/home/kbot/dev/work"
    And the program "core.sh load" prints "Loading the labels of the workarea products..."
    When the operator runs "kbot-installer load"
    Then the only command run is "/home/kbot/dev/work/bin/core.sh load"
    And the output contains, in order:
      | line                                            |
      | Loading the labels of the workarea products... |
      | Load completed successfully.                    |
    And the output ends with "Load completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-05-02 @BR-04 @BR-05
  Scenario Outline: An object flag is forwarded to the loader as its long option (BR-04, BR-05)
    Given a kbot workarea exists in "/home/kbot/work"
    When the operator runs "kbot-installer load -w /home/kbot/work <flag>"
    Then the only command run is "/home/kbot/work/bin/core.sh load <forwarded>"
    And the output ends with "Load completed successfully."
    And the exit code is 0

    Examples:
      | flag        | forwarded            | rule  |
      | -l          | --labels             | BR-04 |
      | --labels    | --labels             | BR-04 |
      | -p          | --profiles           | BR-04 |
      | -M          | --mcp-configurations | BR-04 |
      | -v          | --datasets           | BR-04 |
      | --workflow  | --workflow           | BR-05 |
      | --themes    | --themes             | BR-05 |
      | --widget    | --widget             | BR-05 |

  @since-2026.01 @AC-KBOT-INST-05-03 @BR-04 @BR-06 @BR-07 @BR-08
  Scenario: Object flags, products and customer products are combined (BR-04, BR-06, BR-07, BR-08)
    Given a kbot workarea exists in "/home/kbot/work"
    When the operator runs "kbot-installer load -w /home/kbot/work -l --workflow -M --products jira --products ithd --with-customer"
    Then the only command run is "/home/kbot/work/bin/core.sh load --labels --workflow --mcp-configurations --products jira ithd --with-customer"
    And the output ends with "Load completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-05-04 @BR-11
  Scenario: The load fails in the workarea (BR-11, error)
    Given a kbot workarea exists in "/home/kbot/work"
    And the program "core.sh load --profiles" exits with code 1
    When the operator runs "kbot-installer load -w /home/kbot/work --profiles"
    Then the error output contains "Error loading data: '/home/kbot/work/bin/core.sh load --profiles' failed (exit 1)."
    And the output does not contain "Load completed successfully."
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-05-05 @BR-12
  Scenario: The load is run on a directory that is not a workarea (BR-12, error)
    Given the directory "/tmp/empty" exists
    And the directory "/tmp/empty/bin" does not exist
    When the operator runs "kbot-installer load -w /tmp/empty"
    Then the error output contains "Error loading data: [Errno 2] No such file or directory: '/tmp/empty/bin/core.sh'"
    And the output does not contain "Load completed successfully."
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-05-06 @BR-09 @BR-13 @BR-14
  Scenario: Train the ML models of a workarea (BR-09, BR-13, BR-14)
    Given a kbot workarea exists in "/home/kbot/work"
    And the program "kbot.sh learn" prints "Training the intention classifiers..."
    When the operator runs "kbot-installer learn -w /home/kbot/work"
    Then the only command run is "/home/kbot/work/bin/kbot.sh learn"
    And the output contains, in order:
      | line                                  |
      | Training the intention classifiers... |
      | Learn completed successfully.         |
    And the output ends with "Learn completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-05-07 @BR-15
  Scenario: The training fails in the workarea (BR-15, error)
    Given a kbot workarea exists in "/home/kbot/work"
    And the program "kbot.sh learn" exits with code 2
    When the operator runs "kbot-installer learn -w /home/kbot/work"
    Then the error output contains "Error learning models: '/home/kbot/work/bin/kbot.sh learn' failed (exit 2)."
    And the output does not contain "Learn completed successfully."
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-05-08 @BR-16
  Scenario: The training is run on a directory that is not a workarea (BR-16, error)
    Given the directory "/tmp/empty" exists
    And the directory "/tmp/empty/bin" does not exist
    When the operator runs "kbot-installer learn -w /tmp/empty"
    Then the error output contains "Error learning models: [Errno 2] No such file or directory: '/tmp/empty/bin/kbot.sh'"
    And the output does not contain "Learn completed successfully."
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-05-09 @BR-17 @BR-18
  Scenario Outline: The standalone commands behave like the kbot-installer subcommands (BR-17, BR-18)
    Given a kbot workarea exists in "/home/kbot/work"
    When the operator runs "<standalone>"
    Then the only command run is "<script>"
    And the output ends with "<message>"
    And the exit code is 0

    Examples:
      | standalone                              | script                                       | message                         | rule  |
      | kbot-load -w /home/kbot/work --profiles | /home/kbot/work/bin/core.sh load --profiles  | Load completed successfully.    | BR-17 |
      | kbot-learn -w /home/kbot/work           | /home/kbot/work/bin/kbot.sh learn            | Learn completed successfully.   | BR-18 |
