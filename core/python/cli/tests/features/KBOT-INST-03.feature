# language: en
Feature: KBOT-INST-03 Update

  Background:
    Given the environment variable NEXUS_USERNAME is "kbot"
    And the environment variable NEXUS_PASSWORD is "secret"
    And the directory "/home/kbot/dev/installer" exists
    And the directory "/home/kbot/dev/work" exists

  @since-2026.01 @AC-KBOT-INST-03-01 @BR-02 @BR-12 @BR-17 @BR-29 @BR-38 @BR-43
  Scenario: Update the installer directory and the workarea (nominal case) (BR-02, BR-12, BR-17, BR-29, BR-38, BR-43)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/installer/kbot/core/python/kbot.py" contains "kbot"
    And the file "/home/kbot/dev/installer/kbot/bin/pip3.sh" contains "#!/bin/sh"
    And the file "/home/kbot/dev/installer/kbot/requirements.txt" contains "requests"
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.3" and PostgreSQL "16"
    And the installer directory "/home/kbot/dev/installer" holds the product "ithd" of type "solution" with parents "kbot"
    And the file "/home/kbot/dev/installer/ithd/requirements.txt" contains "jira"
    And the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution" with parents "kbot"
    And the product "acme" in "/home/kbot/dev/installer" was downloaded from storage at commit "1a2b3c4d5e" of branch "release-2026.01-dev"
    And the file "/home/kbot/dev/installer/acme/removed_in_new_version.txt" contains "old"
    And the storage holds the product "acme" version "2026.01" at commit "6f7a8b9c0d" of branch "release-2026.01-dev" with parents "kbot"
    When the operator runs "kbot-installer update --installer --workarea --how smooth -i /home/kbot/dev/installer -w /home/kbot/dev/work"
    Then the download table shows "acme" from "storage" with status "✅ Success" and details "release-2026.01-dev 1a2b3c4d5e → 6f7a8b9c0d"
    And the product "acme" is downloaded from storage at branch "release-2026.01-dev"
    And the file "/home/kbot/dev/installer/acme/description.json" contains "6f7a8b9c0d"
    And "/home/kbot/dev/installer/acme/removed_in_new_version.txt" no longer exists
    And "/home/kbot/dev/work/products/acme" is a symlink to "/home/kbot/dev/installer/acme"
    And "/home/kbot/dev/work/products/ithd" is a symlink to "/home/kbot/dev/installer/ithd"
    And "/home/kbot/dev/work/core/python/kbot.py" is a symlink to "/home/kbot/dev/installer/kbot/core/python/kbot.py"
    And the command ran, in order:
      | command                                                                                   |
      | /home/kbot/dev/installer/kbot/bin/pip3.sh install -r /home/kbot/dev/installer/ithd/requirements.txt |
      | /home/kbot/dev/installer/kbot/bin/pip3.sh install -r /home/kbot/dev/installer/kbot/requirements.txt |
    And the output ends with "Update completed successfully."
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-02 @BR-01
  Scenario: Refuse an update without target (BR-01, error)
    Given the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution"
    And the product "acme" in "/home/kbot/dev/installer" was downloaded from storage at commit "1a2b3c4d5e" of branch "release-2026.01-dev"
    And the storage holds the product "acme" version "2026.01" at commit "6f7a8b9c0d" of branch "release-2026.01-dev"
    When the operator runs "kbot-installer update -i /home/kbot/dev/installer"
    Then the output contains "Nothing to update: specify what to update ('--installer' and/or '--workarea')."
    And the exit code is 2
    And nothing is downloaded
    And the file "/home/kbot/dev/installer/acme/description.json" contains "1a2b3c4d5e"
    And the directory "/home/kbot/dev/work" is empty
    And the command did not run "pip3.sh"

  @since-2026.01 @AC-KBOT-INST-03-03 @BR-03 @BR-05
  Scenario: Default directories and default strategy (BR-03, BR-05)
    Given the operator's home directory is "/home/kbot"
    And the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And "/home/kbot/dev/work/core/python/old.py" is a symlink to "/home/kbot/dev/installer/kbot/core/python/old.py"
    And the operator will answer "n" to "Broken symlink /home/kbot/dev/work/core/python/old.py. Rebuild it? [Y/n] "
    When the operator runs "kbot-installer update --workarea"
    Then "/home/kbot/dev/work/products/kbot" is a symlink to "/home/kbot/dev/installer/kbot"
    And the question "Broken symlink /home/kbot/dev/work/core/python/old.py. Rebuild it? [Y/n] " is asked
    And "/home/kbot/dev/work/core/python/old.py" is a symlink to "/home/kbot/dev/installer/kbot/core/python/old.py"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-04 @BR-04 @BR-05
  Scenario Outline: Options used by one target only (BR-04, BR-05)
    Given the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution"
    And the product "acme" in "/home/kbot/dev/installer" was downloaded from storage at commit "1a2b3c4d5e" of branch "release-2026.01-dev"
    And the installer directory "/home/kbot/dev/installer" was installed from bundle "ev-basic" version "2026.01.0001"
    And the storage holds the release "2026.01.0002" of the bundle "ev-basic" pinning:
      | product | commit     | branch              |
      | acme    | 6f7a8b9c0d | release-2026.01-dev |
    And the storage holds the product "acme" version "2026.01" at commit "6f7a8b9c0d" of branch "release-2026.01-dev"
    And the file "/home/kbot/dev/work/var/log/kbot.log" contains "started"
    When the operator runs "kbot-installer update <options>"
    Then the bundle "ev-basic-2026.01.0002" is read from the "bundles" area of the "<backend>" storage
    And the products downloaded from the "artifacts" area of the "<backend>" storage are "acme"
    And the file "/home/kbot/dev/work/var/log/kbot.log" contains "started"
    And the directory "/home/kbot/dev/work/products" does not exist
    And the exit code is 0

    Examples:
      | options                  | backend | rule  |
      | --installer              | nexus   | BR-04 |
      | --installer --storage s3 | s3      | BR-04 |
      | --installer --how strict | nexus   | BR-05 |

  @since-2026.01 @AC-KBOT-INST-03-05 @BR-06 @BR-08 @BR-09 @BR-10
  Scenario: Move a bundle install to the latest bundle of the same major.minor (BR-06, BR-08, BR-09, BR-10)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the product "kbot" in "/home/kbot/dev/installer" was downloaded from storage at commit "b7c1d2e3f4" of branch "release-2025.03-dev"
    And the installer directory "/home/kbot/dev/installer" holds the product "ithd" of type "solution" with parents "kbot"
    And the product "ithd" in "/home/kbot/dev/installer" was downloaded from storage at commit "c8d9e0f1a2" of branch "release-2025.03-dev"
    And the file "/home/kbot/dev/installer/ithd/removed_in_new_version.txt" contains "old"
    And the installer directory "/home/kbot/dev/installer" was installed from bundle "ev-basic" version "2025.03.0016"
    And the storage holds the release "2025.03.0017" of the bundle "ev-basic" pinning:
      | product | commit     | branch              |
      | kbot    | b7c1d2e3f4 | release-2025.03-dev |
      | ithd    | c8d9e0f1a2 | release-2025.03-dev |
    And the storage holds the release "2025.3.0018" of the bundle "ev-basic" pinning:
      | product | commit     | branch              |
      | kbot    | b7c1d2e3f4 | release-2025.03-dev |
      | ithd    | d4e5f6a7b8 | release-2025.03-dev |
    And the storage holds the release "2026.01.0001" of the bundle "ev-basic" pinning:
      | product | commit     | branch              |
      | kbot    | e9f0a1b2c3 | release-2026.01-dev |
      | ithd    | f4a5b6c7d8 | release-2026.01-dev |
    And the storage holds the product "ithd" version "2025.03" at commit "d4e5f6a7b8" of branch "release-2025.03-dev" with parents "kbot"
    When the operator runs "kbot-installer update --installer"
    Then the bundle "ev-basic-2025.3.0018" is read from the "bundles" area of the "nexus" storage
    And the products downloaded from the "artifacts" area of the "nexus" storage are "ithd"
    And the download table shows "kbot" from "storage (cached)" with status "✔ Up to date"
    And the file "/home/kbot/dev/installer/kbot/description.json" contains "b7c1d2e3f4"
    And the product "ithd" is downloaded from storage at commit "d4e5f6a7b8" of branch "release-2025.03-dev"
    And "/home/kbot/dev/installer/ithd/removed_in_new_version.txt" no longer exists
    And the file "/home/kbot/dev/installer/ithd/description.json" contains "d4e5f6a7b8"
    And the installer directory "/home/kbot/dev/installer" is described by the bundle "ev-basic" version "2025.3.0018"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-06 @BR-07
  Scenario: No bundle published for the installed major.minor (BR-07, error)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the product "kbot" in "/home/kbot/dev/installer" was downloaded from storage at commit "b7c1d2e3f4" of branch "release-2025.03-dev"
    And the installer directory "/home/kbot/dev/installer" was installed from bundle "ev-basic" version "2025.03.0016"
    And the storage holds the release "2026.01.0001" of the bundle "ev-basic" pinning:
      | product | commit     | branch              |
      | kbot    | e9f0a1b2c3 | release-2026.01-dev |
    And the storage holds the release "2025.03.0017" of the bundle "ev-premium" pinning:
      | product | commit     | branch              |
      | kbot    | e9f0a1b2c3 | release-2025.03-dev |
    When the operator runs "kbot-installer update --installer"
    Then the error output contains "Error updating: No bundle 'ev-basic' 2025.03.* found in storage"
    And nothing is downloaded
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-03-07 @BR-11 @BR-20
  Scenario: Local copies of a bundle install are pulled or kept, never replaced (BR-11, BR-20)
    Given the installer directory "/home/kbot/dev/installer" was installed from bundle "ev-basic" version "2025.03.0016"
    And the product "kbot" in "/home/kbot/dev/installer" is a git working copy on branch "release-2025.03-dev"
    And the remote of the git working copy "/home/kbot/dev/installer/kbot" has a new commit on branch "release-2025.03-dev"
    And the storage holds the release "2025.03.0017" of the bundle "ev-basic" pinning:
      | product | commit     | branch              |
      | kbot    | 6f7a8b9c0d | release-2025.03-dev |
    When the operator runs "kbot-installer update --installer"
    Then the download table rows are, in order:
      | product | provider | status     |
      | kbot    | git      | ✅ Success |
      | kbot    | local    | 📌 Kept    |
    And the download table shows "kbot" from "local" with status "📌 Kept" and details "Kept local git working copy (expected commit 6f7a8b9c0d)"
    And the git working copy "/home/kbot/dev/installer/kbot" is on branch "release-2025.03-dev" at the head of origin
    And the directory "/home/kbot/dev/installer/kbot/.git" exists
    And nothing is downloaded
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-08 @BR-14
  Scenario: Skip the download when the published latest build is the installed commit (BR-14)
    Given the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution"
    And the product "acme" in "/home/kbot/dev/installer" was downloaded from storage at commit "1a2b3c4d5e" of branch "release-2026.01-dev"
    And the storage holds the product "acme" version "2026.01" at commit "1a2b3c4d5e" of branch "release-2026.01-dev"
    When the operator runs "kbot-installer update --installer"
    Then nothing is downloaded
    And the download table shows "acme" from "storage" with status "✔ Up to date" and details "release-2026.01-dev already at 1a2b3c4d5e"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-09 @BR-15
  Scenario: Keep the folder when the downloaded artifact holds the installed commit (BR-15)
    Given the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution"
    And the product "acme" in "/home/kbot/dev/installer" was downloaded from storage at commit "1a2b3c4d5e" of branch "release-2026.01-dev"
    And the file "/home/kbot/dev/installer/acme/marker" contains "local"
    And the storage holds the product "acme" version "2026.01" at commit "1a2b3c4d5e" of branch "release-2026.01-dev"
    And the storage publishes no description next to the latest "release-2026.01-dev" artifact of "acme"
    When the operator runs "kbot-installer update --installer"
    Then the product "acme" is downloaded from storage at branch "release-2026.01-dev"
    And the file "/home/kbot/dev/installer/acme/marker" contains "local"
    And the download table shows "acme" from "storage" with status "✔ Up to date" and details "release-2026.01-dev already at 1a2b3c4d5e"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-10 @BR-13 @BR-16 @BR-18
  Scenario Outline: Storage product that cannot be updated keeps its folder (BR-13, BR-16, BR-18, error)
    Given the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution"
    And the product "acme" in "/home/kbot/dev/installer" was downloaded from storage at commit "1a2b3c4d5e" of branch "release-2026.01-dev"
    And the storage holds the product "acme" version "2026.01" at commit "6f7a8b9c0d" of branch "release-2026.01-dev"
    And <situation>
    When the operator runs "kbot-installer update --installer"
    Then the download table shows "acme" from "storage" with status "❌ Error" and details "<message>"
    And the file "/home/kbot/dev/installer/acme/description.json" contains "1a2b3c4d5e"
    And the file "/home/kbot/dev/installer/acme/description.xml" contains "acme"
    And the error output contains "Update finished with errors for: acme"
    And the exit code is 1

    Examples:
      | situation                                                                                                                   | message                                   | rule  |
      | the product "acme" in "/home/kbot/dev/installer" was downloaded from storage at commit "1a2b3c4d5e" without a build branch | No build branch in description.json       | BR-13 |
      | the storage holds the product "acme" version "2026.01" at commit "6f7a8b9c0d" of branch "release-2026.01-dev" without a description.xml | Downloaded archive has no description.xml | BR-16 |
      | moving a folder into "/home/kbot/dev/installer/acme" fails with "Device or resource busy"                                 | [Errno 16] Device or resource busy        | BR-18 |

  @since-2026.01 @AC-KBOT-INST-03-11 @BR-19
  Scenario Outline: Symlinks and local builds are kept (BR-19)
    Given the installer directory "/home/kbot/dev/git" holds the product "kbot" of type "framework"
    And <kind>
    When the operator runs "kbot-installer update --installer"
    Then nothing is downloaded
    And the file "/home/kbot/dev/installer/kbot/description.xml" contains "kbot"
    And "/home/kbot/dev/installer/kbot/description.json" no longer exists
    And the download table shows "kbot" from "local" with status "📌 Kept" and details "<details>"
    And the exit code is 0

    Examples:
      | kind                                                                         | details            | rule  |
      | "/home/kbot/dev/installer/kbot" is a symlink to "/home/kbot/dev/git/kbot"    | Kept local symlink | BR-19 |
      | the product "kbot" in "/home/kbot/dev/installer" is a local build            | Kept local build   | BR-19 |

  @since-2026.01 @AC-KBOT-INST-03-12 @BR-21 @BR-28
  Scenario: Refuse to update a git working copy with uncommitted changes (BR-21, BR-28, error)
    Given the product "kbot" in "/home/kbot/dev/installer" is a git working copy on branch "release-2026.01-dev"
    And the product "ithd" in "/home/kbot/dev/installer" is a git working copy on branch "release-2026.01-dev"
    And the git working copy "/home/kbot/dev/installer/kbot" has uncommitted changes in "a.py, b.py, c.py, d.py, e.py, f.py, g.py"
    And the remote of the git working copy "/home/kbot/dev/installer/kbot" has a new commit on branch "release-2026.01-dev"
    And the remote of the git working copy "/home/kbot/dev/installer/ithd" has a new commit on branch "release-2026.01-dev"
    When the operator runs "kbot-installer update --installer"
    Then the git working copy "/home/kbot/dev/installer/kbot" did not fetch the new commit of "release-2026.01-dev"
    And the file "/home/kbot/dev/installer/kbot/a.py" contains "local change"
    And the download table shows "kbot" from "git" with status "❌ Error" and details "Uncommitted changes: a.py, b.py, c.py, d.py, e.py (+2 more)"
    And the git working copy "/home/kbot/dev/installer/ithd" is on branch "release-2026.01-dev" at the head of origin
    And the error output contains "Update finished with errors for: kbot"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-03-13 @BR-22
  Scenario: Untracked files do not block a git update (BR-22)
    Given the product "kbot" in "/home/kbot/dev/installer" is a git working copy on branch "release-2026.01-dev"
    And the file "/home/kbot/dev/installer/kbot/notes.txt" contains "notes"
    And the remote of the git working copy "/home/kbot/dev/installer/kbot" has a new commit on branch "release-2026.01-dev"
    When the operator runs "kbot-installer update --installer"
    Then the git working copy "/home/kbot/dev/installer/kbot" is on branch "release-2026.01-dev" at the head of origin
    And the file "/home/kbot/dev/installer/kbot/notes.txt" contains "notes"
    And the download table shows "kbot" from "git" with status "✅ Success" and details starting with "release-2026.01-dev "
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-14 @BR-23 @BR-24 @BR-25 @BR-27
  Scenario Outline: Choose the branch a git working copy is pulled on (BR-23, BR-24, BR-25, BR-27)
    Given the product "kbot" in "/home/kbot/dev/installer" is a git working copy of version "<version>" on branch "<current>"
    And the remote of the git working copy "/home/kbot/dev/installer/kbot" has the branches "<remote branches>"
    And the remote of the git working copy "/home/kbot/dev/installer/kbot" has a new commit on branch "<target>"
    When the operator runs "kbot-installer update --installer"
    Then the git working copy "/home/kbot/dev/installer/kbot" is on branch "<target>" at the head of origin
    And the download table shows "kbot" from "git" with status "✅ Success" and details starting with "<target> "
    And the exit code is 0

    Examples:
      | version | current         | remote branches                      | target              | rule  |
      | 2026.01 | release-2026.01 | release-2026.01, release-2026.01-dev | release-2026.01     | BR-23 |
      | 2026.01 | feature/x       | release-2026.01, release-2026.01-dev | release-2026.01-dev | BR-24 |
      | 2026.01 | feature/x       | release-2026.01                      | release-2026.01     | BR-24 |
      |         | master          | master                               | master              | BR-25 |

  @since-2026.01 @AC-KBOT-INST-03-15 @BR-24 @BR-25 @BR-26
  Scenario Outline: Git working copy whose branch cannot be updated (BR-24, BR-25, BR-26, error)
    Given <situation>
    When the operator runs "kbot-installer update --installer"
    Then the download table shows "kbot" from "git" with status "❌ Error" and details "<message>"
    And the error output contains "Update finished with errors for: kbot"
    And the exit code is 1

    Examples:
      | situation                                                                                                        | message                                                                 | rule  |
      | the product "kbot" in "/home/kbot/dev/installer" is a git working copy of version "2026.01" on branch "feature/x" | None of the branches release-2026.01-dev, release-2026.01 exists        | BR-24 |
      | the product "kbot" in "/home/kbot/dev/installer" is a git working copy on a detached HEAD                         | Detached HEAD and no version in description.xml: cannot choose a branch | BR-25 |

    @known-defect
    Examples:
      | situation                                                                                                                            | message                                                                                       | rule  |
      | the product "kbot" in "/home/kbot/dev/installer" is a git working copy whose merge of "release-2026.01-dev" conflicts on "core/a.py" | Pulling 'origin/release-2026.01-dev' left 1 conflicted file(s) to resolve manually: core/a.py | BR-26 |

  @since-2026.01 @AC-KBOT-INST-03-16 @BR-27
  Scenario: Git working copy already up to date (BR-27)
    Given the product "kbot" in "/home/kbot/dev/installer" is a git working copy on branch "release-2026.01-dev"
    When the operator runs "kbot-installer update --installer"
    Then the git working copy "/home/kbot/dev/installer/kbot" is on branch "release-2026.01-dev" at the head of origin
    And the download table shows "kbot" from "git" with status "✔ Up to date" and details "release-2026.01-dev already up to date"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-17 @BR-02 @BR-28
  Scenario: A failed product does not stop the workarea update (BR-02, BR-28, error)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/installer/kbot/README" contains "kbot"
    And the file "/home/kbot/dev/installer/kbot/bin/pip3.sh" contains "#!/bin/sh"
    And the file "/home/kbot/dev/installer/kbot/requirements.txt" contains "requests"
    And the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.3" and PostgreSQL "16"
    And the installer directory "/home/kbot/dev/installer" holds the product "qakeys" of type "solution"
    And the product "qakeys" in "/home/kbot/dev/installer" was downloaded from storage at commit "0a0b0c0d0e" without a build branch
    And the installer directory "/home/kbot/dev/installer" holds the product "acme" of type "solution"
    And the product "acme" in "/home/kbot/dev/installer" was downloaded from storage at commit "1a2b3c4d5e" of branch "release-2026.01-dev"
    And the storage holds the product "acme" version "2026.01" at commit "6f7a8b9c0d" of branch "release-2026.01-dev"
    And "/home/kbot/dev/work/extra/README" is a symlink to "/home/kbot/dev/installer/kbot/README"
    When the operator runs "kbot-installer update --installer --workarea --how repair"
    Then the download table shows "acme" from "storage" with status "✅ Success" and details "release-2026.01-dev 1a2b3c4d5e → 6f7a8b9c0d"
    And the download table shows "qakeys" from "storage" with status "❌ Error" and details "No build branch in description.json"
    And "/home/kbot/dev/work/extra/README" no longer exists
    And "/home/kbot/dev/work/products/acme" is a symlink to "/home/kbot/dev/installer/acme"
    And the command ran "/home/kbot/dev/installer/kbot/bin/pip3.sh install -r /home/kbot/dev/installer/kbot/requirements.txt"
    And the error output contains "Update finished with errors for: qakeys"
    And the exit code is 1

  @since-2026.01 @AC-KBOT-INST-03-18 @BR-30 @BR-33
  Scenario Outline: Interactive strategy asks before removing a broken symlink (BR-30, BR-33)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And "/home/kbot/dev/work/core/python/old.py" is a symlink to "/home/kbot/dev/installer/kbot/core/python/old.py"
    And the operator will answer "<answer>" to "Broken symlink /home/kbot/dev/work/core/python/old.py. Rebuild it? [Y/n] "
    When the operator runs "kbot-installer update --workarea --how interactive"
    Then the question "Broken symlink /home/kbot/dev/work/core/python/old.py. Rebuild it? [Y/n] " is asked
    And <outcome>
    And the output ends with "Update completed successfully."

    Examples:
      | answer | outcome                                                                                                       | rule  |
      | y      | "/home/kbot/dev/work/core/python/old.py" no longer exists                                                    | BR-30 |
      |        | "/home/kbot/dev/work/core/python/old.py" no longer exists                                                    | BR-33 |
      | NO     | "/home/kbot/dev/work/core/python/old.py" is a symlink to "/home/kbot/dev/installer/kbot/core/python/old.py" | BR-33 |

  @since-2026.01 @AC-KBOT-INST-03-19 @BR-31
  Scenario: Interactive strategy asks before refreshing an outdated copy (BR-31)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/installer/kbot/core/python/RunBot.py" contains "new"
    And the file "/home/kbot/dev/work/core/python/RunBot.py" contains "old"
    And the operator will answer "n" to "Outdated copy /home/kbot/dev/work/core/python/RunBot.py. Refresh it from /home/kbot/dev/installer/kbot/core/python/RunBot.py? [Y/n] "
    When the operator runs "kbot-installer update --workarea"
    Then the question "Outdated copy /home/kbot/dev/work/core/python/RunBot.py. Refresh it from /home/kbot/dev/installer/kbot/core/python/RunBot.py? [Y/n] " is asked
    And the file "/home/kbot/dev/work/core/python/RunBot.py" contains "old"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-20 @BR-32
  Scenario: Interactive strategy asks before removing the unused tests directory (BR-32)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/work/tests/test_old.py" contains "old"
    And the operator will answer "y" to "Not used directory 'tests' (/home/kbot/dev/work/tests). Remove it? [Y/n] "
    When the operator runs "kbot-installer update --workarea"
    Then the question "Not used directory 'tests' (/home/kbot/dev/work/tests). Remove it? [Y/n] " is asked
    And the directory "/home/kbot/dev/work/tests" does not exist
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-21 @BR-33
  Scenario: Invalid answer to a prompt (BR-33)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And "/home/kbot/dev/work/core/python/old.py" is a symlink to "/home/kbot/dev/installer/kbot/core/python/old.py"
    And the operator will answer "maybe" to "Broken symlink /home/kbot/dev/work/core/python/old.py. Rebuild it? [Y/n] "
    And the operator will answer "n" to "Broken symlink /home/kbot/dev/work/core/python/old.py. Rebuild it? [Y/n] "
    When the operator runs "kbot-installer update --workarea"
    Then the output contains 'Answer either "y" or "n".'
    And the question "Broken symlink /home/kbot/dev/work/core/python/old.py. Rebuild it? [Y/n] " is asked 2 times
    And "/home/kbot/dev/work/core/python/old.py" is a symlink to "/home/kbot/dev/installer/kbot/core/python/old.py"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-22 @BR-34
  Scenario Outline: Non-interactive strategies never prompt (BR-34)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/installer/kbot/core/python/RunBot.py" contains "new"
    And the file "/home/kbot/dev/work/core/python/RunBot.py" contains "old"
    And the file "/home/kbot/dev/work/tests/test_old.py" contains "old"
    When the operator runs "kbot-installer update --workarea --how <how>"
    Then no question is asked
    And the directory "/home/kbot/dev/work/tests" does not exist
    And the file "/home/kbot/dev/work/core/python/RunBot.py" contains "new"
    And the exit code is 0

    Examples:
      | how    | rule  |
      | smooth | BR-34 |
      | repair | BR-34 |
      | strict | BR-34 |

  @since-2026.01 @AC-KBOT-INST-03-23 @BR-35
  Scenario: Smooth strategy keeps broken symlinks (BR-35)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And "/home/kbot/dev/work/core/python/old.py" is a symlink to "/home/kbot/dev/installer/kbot/core/python/old.py"
    When the operator runs "kbot-installer update --workarea --how smooth"
    Then "/home/kbot/dev/work/core/python/old.py" is a symlink to "/home/kbot/dev/installer/kbot/core/python/old.py"
    And no question is asked
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-24 @BR-36
  Scenario: Repair strategy relinks the workarea (BR-36)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/installer/kbot/core/python/kbot.py" contains "kbot"
    And the file "/home/kbot/dev/installer/legacy/core/python/kbot.py" contains "legacy"
    And "/home/kbot/dev/work/core/python/kbot.py" is a symlink to "/home/kbot/dev/installer/legacy/core/python/kbot.py"
    And "/home/kbot/dev/work/lib/broken.py" is a symlink to "/opt/missing/broken.py"
    And the directory "/opt/tools" exists
    And "/home/kbot/dev/work/tools" is a symlink to "/opt/tools"
    And the file "/home/kbot/dev/work/var/kbot.db" contains "data"
    When the operator runs "kbot-installer update --workarea --how repair"
    Then "/home/kbot/dev/work/core/python/kbot.py" is a symlink to "/home/kbot/dev/installer/kbot/core/python/kbot.py"
    And "/home/kbot/dev/work/lib/broken.py" no longer exists
    And "/home/kbot/dev/work/tools" is a symlink to "/opt/tools"
    And the file "/home/kbot/dev/work/var/kbot.db" contains "data"
    And no question is asked
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-25 @BR-37
  Scenario: Strict strategy rebuilds the workarea from scratch (BR-37)
    Given the installer directory "/home/kbot/dev/installer" holds the product "kbot" of type "framework"
    And the file "/home/kbot/dev/installer/kbot/core/python/kbot.py" contains "kbot"
    And the file "/home/kbot/dev/work/var/log/kbot.log" contains "started"
    When the operator runs "kbot-installer update --workarea --how strict"
    Then no question is asked
    And "/home/kbot/dev/work/var/log/kbot.log" no longer exists
    And "/home/kbot/dev/work/products/kbot" is a symlink to "/home/kbot/dev/installer/kbot"
    And "/home/kbot/dev/work/core/python/kbot.py" is a symlink to "/home/kbot/dev/installer/kbot/core/python/kbot.py"
    And the exit code is 0

  @since-2026.01 @AC-KBOT-INST-03-26 @BR-38 @BR-39
  Scenario Outline: Python requirements step (BR-38, BR-39)
    Given the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.3" and PostgreSQL "16"
    And the product "acme" in "/home/kbot/dev/installer" is a local build
    And the file "/home/kbot/dev/installer/acme/requirements.txt" contains "requests"
    And <situation>
    When the operator runs "kbot-installer update --installer <options>"
    Then <pip>
    And <warning>
    And the output ends with "Update completed successfully."
    And the exit code is 0

    Examples:
      | situation                                                                   | options                    | pip                                                                                                                 | warning                                                                                                    | rule  |
      | the file "/home/kbot/dev/installer/kbot/bin/pip3.sh" contains "#!/bin/sh"   |                            | the command ran "/home/kbot/dev/installer/kbot/bin/pip3.sh install -r /home/kbot/dev/installer/acme/requirements.txt" | the warning "Skipping product Python requirements" is not logged                                          | BR-38 |
      | the file "/home/kbot/dev/installer/kbot/bin/pip3.sh" contains "#!/bin/sh"   | --skip-python-requirements | the command did not run "pip3.sh"                                                                                   | the warning "Skipping product Python requirements" is not logged                                          | BR-38 |
      | the directory "/home/kbot/dev/installer/kbot" does not exist                |                            | the command did not run "pip3.sh"                                                                                   | the warning "Skipping product Python requirements: '/home/kbot/dev/installer/kbot/bin/pip3.sh' not found." is logged | BR-39 |

  @since-2026.01 @AC-KBOT-INST-03-27 @BR-40 @BR-41
  Scenario Outline: Python requirements cannot be installed (BR-40, BR-41, error)
    Given the product "acme" in "/home/kbot/dev/installer" is a local build
    And the file "/home/kbot/dev/installer/acme/requirements.txt" contains "requests"
    And the file "/home/kbot/dev/installer/kbot/bin/pip3.sh" contains "#!/bin/sh"
    And the program "pip3.sh" exits with code 1
    And <situation>
    When the operator runs "kbot-installer update --installer"
    Then the error output contains "Error updating: <message>"
    And the exit code is 1

    Examples:
      | situation                                                                                            | message                                                                                            | rule  |
      | the directory "/home/kbot/dev/installer/3rdparty" does not exist                                     | Cannot install Python requirements: the 3rdparty Python is missing from '/home/kbot/dev/installer' | BR-40 |
      | the installer directory "/home/kbot/dev/installer" holds a 3rdparty with Python "3.12.3" and PostgreSQL "16" | Failed to install Python requirements for 'acme' (exit 1).                                         | BR-41 |

  @since-2026.01 @AC-KBOT-INST-03-28 @BR-42
  Scenario: Unexpected failure after product failures (BR-42, error)
    Given the installer directory "/home/kbot/dev/installer" holds the product "qakeys" of type "solution"
    And the product "qakeys" in "/home/kbot/dev/installer" was downloaded from storage at commit "0a0b0c0d0e" without a build branch
    And the product "acme" in "/home/kbot/dev/installer" is a local build
    And the file "/home/kbot/dev/installer/acme/requirements.txt" contains "requests"
    And the file "/home/kbot/dev/installer/kbot/bin/pip3.sh" contains "#!/bin/sh"
    And the directory "/home/kbot/dev/installer/3rdparty" does not exist
    When the operator runs "kbot-installer update --installer"
    Then the output contains, in order:
      | line                                                                                                  |
      | Update finished with errors for: qakeys                                                               |
      | Error updating: Cannot install Python requirements: the 3rdparty Python is missing from '/home/kbot/dev/installer' |
    And the exit code is 1
