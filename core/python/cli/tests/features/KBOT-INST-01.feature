# language: en
Feature: KBOT-INST-01 Product download and listing

  @since-2026.01 @AC-KBOT-INST-01-01 @BR-10 @BR-11 @BR-16 @BR-20 @BR-21 @BR-22
  Scenario: Download a product with its dependencies (nominal case) (BR-10, BR-11, BR-16, BR-20, BR-21, BR-22)
    Given the environment variable NEXUS_USERNAME is "kbot"
    And the environment variable NEXUS_PASSWORD is "secret"
    And the storage holds the product "jira" version "2025.03" at commit "c0ffee0001" of branch "release-2025.03-dev" with parents "ithd"
    And the storage holds the product "ithd" version "2025.03" at commit "c0ffee0002" of branch "release-2025.03-dev" with parents "kbot"
    And the storage holds the product "kbot" version "2025.03" at commit "c0ffee0003" of branch "release-2025.03-dev"
    And the directory "/home/kbot/dev/installer" exists
    When the operator runs "kbot-installer download -p jira -v 2025.03 -i /home/kbot/dev/installer"
    Then the product "jira" is downloaded from storage at branch "release-2025.03-dev"
    And the product "ithd" is downloaded from storage at branch "release-2025.03-dev"
    And the product "kbot" is downloaded from storage at branch "release-2025.03-dev"
    And the file "/home/kbot/dev/installer/jira/description.xml" contains "jira"
    And the file "/home/kbot/dev/installer/ithd/description.xml" contains "ithd"
    And the file "/home/kbot/dev/installer/kbot/description.xml" contains "kbot"
    And the download table shows "jira" from "storage" with status "✅ Success"
    And the download table shows "ithd" from "storage" with status "✅ Success"
    And the download table shows "kbot" from "storage" with status "✅ Success"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-01-02 @BR-43
  Scenario: Help is shown when no command is given (BR-43)
    When the operator runs "kbot-installer"
    Then the output contains, in order:
      | line                                                                 |
      | Usage: kbot-installer [OPTIONS] [COMMAND] [ARGS]...                  |
      | Kbot Installer - A tool for installing and managing kbot products.   |
      | download                                                             |
      | list                                                                 |
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-01-03 @BR-02
  Scenario Outline: -h is an alias of --help (BR-02)
    When the operator runs "kbot-installer <args> -h"
    Then the output is the same as for "kbot-installer <args> --help"
    And the exit code is 0

    Examples:
      | args     | rule  |
      |          | BR-02 |
      | download | BR-02 |
      | list     | BR-02 |

  @since-2026.01 @AC-KBOT-INST-01-04 @BR-03
  Scenario: Show the installer version (BR-03)
    When the operator runs "kbot-installer --version"
    Then the output is:
      """
      kbot-installer, version 0.1.0
      """
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-01-05 @BR-04
  Scenario Outline: Invalid option values are refused (BR-04, error)
    When the operator runs "<command>"
    Then the output contains "Error: Invalid value for '<option>'"
    And the exit code is 2

    Examples:
      | command                                                   | option     | rule  |
      | kbot-installer download -p jira -v dev --provider gitlab  | --provider | BR-04 |
      | kbot-installer download -p jira -v dev --storage gcs      | --storage  | BR-04 |

  @since-2026.01 @AC-KBOT-INST-01-06 @BR-05
  Scenario: Unexpected error (BR-05, error)
    Given the command "list" fails outside its own error handling with "boom"
    When the operator runs "kbot-installer list"
    Then the output is:
      """
      Error: boom
      """
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-01-07 @BR-06
  Scenario: Ctrl-C stops the command (BR-06)
    Given the environment variable NEXUS_USERNAME is "kbot"
    And the environment variable NEXUS_PASSWORD is "secret"
    And the storage holds the product "jira" version "2026.01" at commit "c0ffee0001" of branch "dev"
    When the operator interrupts "kbot-installer download -p jira -v dev" with Ctrl-C
    Then nothing is downloaded
    And the output ends with "Aborted!"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-01-08 @BR-07 @BR-08
  Scenario Outline: Missing product or version is refused (BR-07, BR-08, error)
    When the operator runs "<command>"
    Then the output contains "Error: <message>"
    And nothing is downloaded
    And the exit code is 2

    Examples:
      | command                                                 | message                                                                              | rule  |
      | kbot-installer download -v 2025.03                      | Option '-p/--product' is required when installing a product.                        | BR-07 |
      | kbot-installer download -b ev-basic-2025.03.0016        | Option '-p/--product' is required when installing from a bundle.                    | BR-07 |
      | kbot-installer download -p jira                         | Option '-v/--version' is required when downloading a product without '-b/--bundle'. | BR-08 |

  @since-2026.01 @AC-KBOT-INST-01-09 @BR-09 @BR-23
  Scenario: Default installer directory is created, no dependencies with --no-rec (BR-09, BR-23)
    Given the operator's home directory is "/home/kbot"
    And the directory "/home/kbot/dev/installer" does not exist
    And the environment variable NEXUS_USERNAME is "kbot"
    And the environment variable NEXUS_PASSWORD is "secret"
    And the storage holds the product "jira" version "2026.01" at commit "c0ffee0001" of branch "dev" with parents "kbot"
    And the storage holds the product "kbot" version "2026.01" at commit "c0ffee0002" of branch "dev"
    When the operator runs "kbot-installer download -p jira -v dev --no-rec"
    Then the directory "/home/kbot/dev/installer" exists
    And the file "/home/kbot/dev/installer/jira/description.xml" contains "jira"
    And the product "jira" is downloaded from storage at branch "dev"
    And the directory "/home/kbot/dev/installer/kbot" does not exist
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-01-10 @BR-10
  Scenario Outline: Version to branch mapping (BR-10)
    Given the environment variable NEXUS_USERNAME is "kbot"
    And the environment variable NEXUS_PASSWORD is "secret"
    And the storage holds the product "jira" version "2025.03" at commit "c0ffee0001" of branch "<branch>"
    When the operator runs "kbot-installer download -p jira -v <version> --no-rec"
    Then the product "jira" is downloaded from storage at branch "<branch>"

    Examples:
      | version     | branch              | rule  |
      | dev         | dev                 | BR-10 |
      | master      | master              | BR-10 |
      | 2025.03-dev | release-2025.03-dev | BR-10 |
      | 2025.03     | release-2025.03-dev | BR-10 |

  @since-2026.01 @AC-KBOT-INST-01-11 @BR-12 @BR-16
  Scenario: Explicit providers in the given order (BR-12, BR-16)
    Given the environment variable NEXUS_USERNAME is "kbot"
    And the environment variable NEXUS_PASSWORD is "secret"
    And the storage holds the product "jira" version "2025.03" at commit "c0ffee0001" of branch "release-2025.03-dev"
    And the git provider "bitbucket" serves the product "jira" on branch "release-2025.03-dev"
    When the operator runs "kbot-installer download -p jira -v 2025.03 --no-rec --provider GitHub --provider bitbucket"
    Then the storage is not read
    And the git providers are tried in order:
      | provider  |
      | github    |
      | bitbucket |
    And the product "jira" is cloned from the git provider "bitbucket" at branch "release-2025.03-dev"
    And the download table shows "jira" from "bitbucket" with status "✅ Success"

  @since-2026.01 @AC-KBOT-INST-01-12 @BR-13 @BR-15
  Scenario: Providers without credentials are skipped (BR-13, BR-15, error)
    Given the environment variable NEXUS_USERNAME is not set
    And the environment variable NEXUS_PASSWORD is not set
    When the operator runs "kbot-installer download -p jira -v dev --provider storage"
    Then the error output contains "Error installing product: No provider could be built from: ['storage']"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-01-13 @BR-14 @BR-19
  Scenario: Storage provider on S3 (BR-14, BR-19)
    Given the environment variable NEXUS_USERNAME is not set
    And the environment variable NEXUS_PASSWORD is not set
    And the storage holds the product "kbot" version "2026.01" at commit "c0ffee0001" of branch "dev"
    When the operator runs "kbot-installer download -p kbot -v dev --no-rec --provider storage --storage s3"
    Then the product "kbot" is downloaded from the "artifacts" area of the "s3" storage
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-01-14 @BR-17
  Scenario: Fallback to the provider branches (BR-17)
    Given the git provider "github" serves the product "jira" on branch "main"
    When the operator runs "kbot-installer download -p jira -v 2031.01 --no-rec --provider github"
    Then the product "jira" is cloned from the git provider "github" at branch "main"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-01-15 @BR-18 @BR-34
  Scenario: Every provider fails (BR-18, BR-34, error)
    Given the environment variable NEXUS_USERNAME is "kbot"
    And the environment variable NEXUS_PASSWORD is "secret"
    When the operator runs "kbot-installer download -p unknown -v dev"
    Then the error output contains "Error installing product: All providers failed to clone repository 'unknown':"
    And the error output contains "StorageProvider object at"
    And the error output contains "GithubProvider object at"
    And the error output contains "BitbucketProvider object at"
    And the output ends with "Aborted!"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-01-16 @BR-24
  Scenario: Downloaded product without description.xml (BR-24, error)
    Given the environment variable NEXUS_USERNAME is "kbot"
    And the environment variable NEXUS_PASSWORD is "secret"
    And the storage holds the product "jira" version "2026.01" at commit "c0ffee0001" of branch "dev" without a description.xml
    When the operator runs "kbot-installer download -p jira -v dev -i /home/kbot/dev/installer"
    Then the error output contains "description.xml not found in /home/kbot/dev/installer/jira"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-01-17 @BR-25 @BR-29
  Scenario Outline: Products already present are skipped (BR-25, BR-29)
    Given the environment variable NEXUS_USERNAME is "kbot"
    And the environment variable NEXUS_PASSWORD is "secret"
    And the installer directory "/home/kbot/dev/installer" holds the product "jira" of type "solution" with parents "ithd"
    And the product "jira" in "/home/kbot/dev/installer" was downloaded from storage at commit "c0ffee0001" of branch "dev"
    And the installer directory "/home/kbot/dev/installer" holds the product "ithd" of type "solution" with parents "kbot"
    And the product "ithd" in "/home/kbot/dev/installer" was downloaded from storage at commit "c0ffee0002" of branch "dev"
    And the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the product "kbot" in "/home/kbot/dev/installer" was downloaded from storage at commit "c0ffee0003" of branch "dev"
    When the operator runs "kbot-installer download -p jira -v dev -i /home/kbot/dev/installer <flag>"
    Then nothing is downloaded
    And the download table <display> "jira" from "storage (cached)" with status "⏭️ Skipped" and details "Already installed"
    And the download table <display> "ithd" from "storage (cached)" with status "⏭️ Skipped" and details "Already installed"
    And the download table <display> "kbot" from "storage (cached)" with status "⏭️ Skipped" and details "Already installed"

    Examples:
      | flag | display       | rule  |
      |      | does not show | BR-29 |

    @known-defect
    Examples:
      | flag | display       | rule  |
      | -V   | shows         | BR-29 |

  @since-2026.01 @AC-KBOT-INST-01-18 @BR-26
  Scenario: Outdated pinned product is replaced (BR-26)
    Given the storage holds the bundle "ev-basic-2025.03.0016" version "2025.03.0016" pinning:
      | product | commit     | branch              |
      | kbot    | b7c1d2e3f4 | release-2025.03-dev |
    And the storage holds the product "kbot" version "2025.03" at commit "b7c1d2e3f4" of branch "release-2025.03-dev"
    And the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the product "kbot" in "/home/kbot/dev/installer" was downloaded from storage at commit "a1b2c3d4e5" of branch "release-2025.03-dev"
    And the file "/home/kbot/dev/installer/kbot/removed_in_new_version.txt" contains "old"
    When the operator runs "kbot-installer download -b ev-basic-2025.03.0016 -p kbot -i /home/kbot/dev/installer"
    Then "/home/kbot/dev/installer/kbot/removed_in_new_version.txt" no longer exists
    And the product "kbot" is downloaded from storage at commit "b7c1d2e3f4" of branch "release-2025.03-dev"
    And the file "/home/kbot/dev/installer/kbot/description.json" contains "b7c1d2e3f4"
    And the download table shows "kbot" from "storage" with status "✅ Success"

  @since-2026.01 @AC-KBOT-INST-01-19 @BR-27 @BR-28
  Scenario Outline: User-managed copies are kept (BR-27, BR-28)
    Given the storage holds the bundle "ev-basic-2025.03.0016" version "2025.03.0016" pinning:
      | product | commit     | branch              |
      | kbot    | b7c1d2e3f4 | release-2025.03-dev |
    And the storage holds the product "kbot" version "2025.03" at commit "b7c1d2e3f4" of branch "release-2025.03-dev"
    And the installer directory "/home/kbot/dev/git" holds the product "kbot" of type "framework"
    And <copy>
    When the operator runs "kbot-installer download -b ev-basic-2025.03.0016 -p kbot -i /home/kbot/dev/installer"
    Then nothing is downloaded
    And the file "/home/kbot/dev/installer/kbot/description.xml" contains "kbot"
    And the download table shows "kbot" from "local" with status "📌 Kept" and details "Kept <kind> (expected commit b7c1d2e3f4)"

    Examples:
      | copy                                                                                         | kind                   | rule  |
      | "/home/kbot/dev/installer/kbot" is a symlink to "/home/kbot/dev/git/kbot"                    | local symlink          | BR-27 |
      | the product "kbot" in "/home/kbot/dev/installer" is a git working copy on branch "dev"       | local git working copy | BR-27 |
      | the product "kbot" in "/home/kbot/dev/installer" is a local build                            | local build            | BR-27 |

  @since-2026.01 @AC-KBOT-INST-01-20 @BR-30 @BR-31 @BR-32 @BR-33
  Scenario: Download a bundle (BR-30, BR-31, BR-32, BR-33)
    Given the storage holds the bundle "ev-basic-2025.03.0016" version "2025.03.0016" pinning:
      | product | commit     | branch              |
      | kbot    | b7c1d2e3f4 | release-2025.03-dev |
      | ithd    | c8d9e0f1a2 | release-2025.03-dev |
      | jira    | d3e4f5a6b7 | release-2025.03-dev |
    And the storage holds the product "kbot" version "2025.03" at commit "b7c1d2e3f4" of branch "release-2025.03-dev"
    And the storage holds the product "ithd" version "2025.03" at commit "c8d9e0f1a2" of branch "release-2025.03-dev" with parents "kbot"
    And the storage holds the product "jira" version "2025.03" at commit "d3e4f5a6b7" of branch "release-2025.03-dev" with parents "ithd"
    And the storage holds the product "ithd-extra" version "2025.03" at commit "e1e1e1e1e1" of branch "release-2025.03-dev"
    And the directory "/home/kbot/dev/installer" exists
    When the operator runs "kbot-installer download -b ev-basic-2025.03.0016 -p kbot -i /home/kbot/dev/installer"
    Then the file "/home/kbot/dev/installer/bundle.json" contains "ev-basic-2025.03.0016"
    And the product "kbot" is downloaded from storage at commit "b7c1d2e3f4" of branch "release-2025.03-dev"
    And the product "ithd" is downloaded from storage at commit "c8d9e0f1a2" of branch "release-2025.03-dev"
    And the product "jira" is downloaded from storage at commit "d3e4f5a6b7" of branch "release-2025.03-dev"
    And the products downloaded from the "artifacts" area of the "nexus" storage are "kbot, ithd, jira"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-01-21 @BR-30 @BR-34
  Scenario: Unknown bundle (BR-30, BR-34, error)
    When the operator runs "kbot-installer download -b ev-unknown-2025.03.0001 -p kbot"
    Then the error output contains "Error installing product: Bundle ev-unknown-2025.03.0001 was not found"
    And the output ends with "Aborted!"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-01-22 @BR-35
  Scenario: List a missing installer directory (BR-35)
    Given the directory "/home/kbot/nothing" does not exist
    When the operator runs "kbot-installer list -i /home/kbot/nothing"
    Then the output is:
      """
      Installer directory does not exist. No products installed.
      """
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-01-23 @BR-36 @BR-37
  Scenario: List an installer directory without products (BR-36, BR-37)
    Given the directory "/home/kbot/dev/installer/tmp" exists
    When the operator runs "kbot-installer list -i /home/kbot/dev/installer"
    Then the output is:
      """
      No products installed.
      """

  @since-2026.01 @AC-KBOT-INST-01-24 @BR-38
  Scenario: Flat list of products (BR-38)
    Given the installer directory "/home/kbot/dev/installer" holds the product "jira" of type "solution" with parents "ithd, kbot"
    And the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    When the operator runs "kbot-installer list -i /home/kbot/dev/installer"
    Then the output is:
      """
      Installed products:
      ==================
      - jira (solution)
        Dependencies: ithd, kbot
      - kbot (framework)
      """

  @since-2026.01 @AC-KBOT-INST-01-25 @BR-39 @BR-40 @known-defect
  Scenario: Dependency tree hides redundant subtrees (BR-39, BR-40)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the installer directory "/home/kbot/dev/installer" holds the product "ithd" of type "solution" with parents "kbot"
    And the installer directory "/home/kbot/dev/installer" holds the product "jira" of type "solution" with parents "ithd, kbot"
    When the operator runs "kbot-installer list --tree -i /home/kbot/dev/installer"
    Then the output contains:
      """
      jira
      ├── ithd (already shown)
      └── kbot (already shown)
      """

  @since-2026.01 @AC-KBOT-INST-01-26 @BR-41 @known-defect
  Scenario: Dependency tree with all subtrees (BR-41)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the installer directory "/home/kbot/dev/installer" holds the product "ithd" of type "solution" with parents "kbot"
    And the installer directory "/home/kbot/dev/installer" holds the product "jira" of type "solution" with parents "ithd, kbot"
    When the operator runs "kbot-installer list --tree -v -i /home/kbot/dev/installer"
    Then the output contains:
      """
      jira
      ├── ithd
      │   └── kbot
      └── kbot (circular)
      """

  @since-2026.01 @AC-KBOT-INST-01-27 @BR-42
  Scenario: List error (BR-42, error)
    Given reading the directory "/home/kbot/dev/installer" fails with "Permission denied"
    When the operator runs "kbot-installer list -i /home/kbot/dev/installer"
    Then the error output contains "Error listing products: "
    And the output ends with "Aborted!"
    And the exit code is 1
