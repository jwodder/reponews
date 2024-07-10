|repostatus| |ci-status| |coverage| |pyversions| |license|

.. |repostatus| image:: https://www.repostatus.org/badges/latest/active.svg
    :target: https://www.repostatus.org/#active
    :alt: Project Status: Active — The project has reached a stable, usable
          state and is being actively developed.

.. |ci-status| image:: https://github.com/jwodder/reponews/actions/workflows/test.yml/badge.svg
    :target: https://github.com/jwodder/reponews/actions/workflows/test.yml
    :alt: CI Status

.. |coverage| image:: https://codecov.io/gh/jwodder/reponews/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/jwodder/reponews

.. |pyversions| image:: https://img.shields.io/pypi/pyversions/reponews.svg
    :target: https://pypi.org/project/reponews/

.. |license| image:: https://img.shields.io/github/license/jwodder/reponews.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

`GitHub <https://github.com/jwodder/reponews>`_
| `PyPI <https://pypi.org/project/reponews/>`_
| `Issues <https://github.com/jwodder/reponews/issues>`_
| `Changelog <https://github.com/jwodder/reponews/blob/master/CHANGELOG.md>`_

Do you want to receive e-mail notifications about new issues, pull requests,
discussions, releases, tags, stargazers, & forks on your GitHub repositories?
Of course you do — but turning on e-mail notifications in GitHub for
repositories you're watching will mean you get an e-mail for every comment on
every issue, which is a bit too much.  ``reponews`` aims for a happy medium:
only e-mailing you about new issues and similar activity — not about comments —
and only on repositories of your choice.  Simply set it up to run under cron or
another job scheduler (sold separately), point it at a compatible e-mail
sending service (also sold separately), and you'll get periodic e-mails listing
new events.

Installation & Setup
====================
``reponews`` requires Python 3.8 or higher.  Just use `pip
<https://pip.pypa.io>`_ for Python 3 (You have pip, right?) to install
``reponews`` and its dependencies::

    python3 -m pip install reponews

Before running ``reponews`` for the first time, you need to `acquire a GitHub
personal access token`__ for fetching details about your repositories via the
GitHub GraphQL API, and you need to create a configuration file containing, at
a minimum:

__ https://docs.github.com/en/authentication/keeping-your-account-and-data
   -secure/creating-a-personal-access-token

- The access token or the path to a file containing it
- The e-mail address that ``reponews`` should send its reports to
- Details on how to send those e-mails

An example configuration file, for sending e-mails to luser@example.com with
the ``sendmail`` command:

.. code:: toml

    [reponews]
    recipient = "luser@example.com"
    auth-token = "..."

    [outgoing]
    method = "command"
    command = ["sendmail", "-i", "-t"]

See "`Configuration`_" below for details.

Example
=======

An example of the sort of e-mail that ``reponews`` might send you::

    [luser/my-repo] ISSUE #42: I found a bug (@bug-finder)
    <https://github.com/luser/my-repo/issues/42>

    @bug-fixer forked luser/my-repo
    <https://github.com/bug.fixer/my-repo>

    [luser/my-repo] PR #43: I fixed that bug (@bug-fixer)
    <https://github.com/luser/my-repo/pull/43>

    ★ @repo-fan starred orgcorp/bigrepo

    [orgcorp/bigrepo] DISCUSSION #123: How do I use this? (@confused-user)
    <https://github.com/orgcorp/bigrepo/discussions/123>

    [theteam/theproject] RELEASE v1.0a1 [prerelease]: v1 Preview (@github-actions[bot])
    <https://github.com/theteam/theproject/releases/tag/v1.0a1>
    > We're gearing up for the first full release!  Here are some changes you'll find:
    >
    > * Added a feature
    > * Fixed a bug

    Now tracking repository luser/brand-new-repo
    <https://github.com/luser/brand-new-repo>
    > This is the repository description.

    No longer tracking repository tmprepos/deleted-repo

    Repository renamed: team-member/new-project → theteam/new-project


Usage
=====

::

    reponews [<options>]

The ``reponews`` command queries GitHub's GraphQL API for new issues, pull
requests, discussions, releases, tags, stargazers, and/or forks on the
repositories specified in its configuration file (by default, all repositories
affiliated with the authenticated user) and composes & sends an e-mail listing
the events in chronological order.  Also included in the report are
notifications about newly-tracked and -untracked repositories and renamed
repositories.  If there is no new activity, no e-mail is sent.

"New" activity is, in the general case, anything that has happened since the
last time ``reponews`` was successfully run (specifically, since the last time
the state file was updated).  The first time ``reponews`` is run, it merely
reports all the repositories that it is now tracking.  If ``reponews`` stops
tracking a repository (usually because the repository listing in the config
file was edited) and then starts tracking it again, it will *not* pick up where
it left off; instead, when it first starts tracking the repository again, it
will mark down that point in time and afterwards only report events occurring
after it.  Similar behavior occurs if ``reponews`` stops tracking a certain
type of activity and then starts tracking it again.

Options
-------

-c PATH, --config PATH          Specify the configuration file to use.  See
                                "`Configuration`_" below for the default config
                                file location.

--dump-repos                    Instead of fetching repository activity, dump
                                the set of tracked repositories and their
                                configured activity preferences as a JSON
                                document

-E FILE, --env FILE             Load environment variables from the given
                                ``.env`` file.  By default, environment
                                variables are loaded from the first file named
                                "``.env``" found by searching from the current
                                directory upwards.

-l LEVEL, --log-level LEVEL     Set the log level to the given value.  Possible
                                values are "``CRITICAL``", "``ERROR``",
                                "``WARNING``", "``INFO``", "``DEBUG``" (all
                                case-insensitive) and their Python integer
                                equivalents.  [default: ``WARNING``]

--print                         Cause ``reponews`` to output the e-mail (as a
                                MIME document) instead of sending it

--print-body                    Cause ``reponews`` to output the body of the
                                e-mail instead of sending it

--save, --no-save               Update/do not update the state file on
                                successful completion [default: ``--save``]


Configuration
=============

``reponews`` is configured via a `TOML <https://toml.io>`_ file whose default
location depends on your OS:

=======  ==================================================================
Linux    ``~/.config/reponews/config.toml``
         or ``$XDG_CONFIG_HOME/reponews/config.toml``
macOS    ``~/Library/Application Support/reponews/config.toml``
Windows  ``%USERPROFILE%\AppData\Local\jwodder\reponews\config.toml``
=======  ==================================================================

This TOML file must contain a ``[reponews]`` table with the following keys &
subtables (all of which are optional unless stated otherwise).  Unknown keys
result in an error.

``recipient`` : e-mail address
    [Required when ``--print-body`` is not given] The e-mail address to which
    ``reponews`` should send its reports.  This can be either a plain e-mail
    address (e.g., ``"me@example.com"``) or a display name with an address in
    angle brackets (e.g., ``"Madam E <me@example.com>"``).  Note that, if the
    display name contains any punctuation, it needs to be enclosed in double
    quotes, which then need to be escaped for use in the TOML string, e.g.,
    ``"\"Joe Q.  Recipient\" <jqr@example.net>"``.

``sender`` : e-mail address
    The ``From:`` address to put on ``reponews``'s e-mails; specified the same
    way as ``recipient``.  If ``sender`` is not specified, it is assumed that
    the e-mail sending mechanism will automatically fill in the ``From:``
    address appropriately.

``subject`` : string
    The subject to apply to ``reponews``'s e-mails; defaults to "[reponews] New
    activity on your GitHub repositories".

``auth-token`` : string
    The GitHub access token to use for interacting with the GitHub API.  If
    ``auth-token`` is not set, the token will be read from the file specified
    by ``auth-token-file``.  If neither key is set, the GitHub token is looked
    up via the following sources, in order:

    - The ``GH_TOKEN`` and ``GITHUB_TOKEN`` environment variables (possibly set
      via the ``.env`` file; see the ``--env`` option under "Options_" above)

    - The gh_ command, if installed

    - The hub_ command's configuration file

    - The ``hub.oauthtoken`` Git config option

    .. _gh: https://github.com/cli/cli
    .. _hub: https://github.com/mislav/hub

``auth-token-file`` : path
    The path to a file containing the GitHub access token to use for
    interacting with the GitHub API.  The file must contain only the token and
    possibly leading and/or trailing whitespace.

    The path may start with a tilde (``~``) to indicate a file in the user's
    home directory.  A relative path will be resolved relative to the directory
    containing the config file.

``state-file`` : path
    The path to the file where ``reponews`` will store repository activity
    state, used to determine the cutoff point for new activity.  The path may
    start with a tilde (``~``) to indicate a file in the user's home directory.
    A relative path will be resolved relative to the directory containing the
    config file.

    The default location for the state file depends on your OS:

    =======  =================================================================
    Linux    ``~/.local/state/reponews/state.json``
             or ``$XDG_STATE_HOME/reponews/state.json``
    macOS    ``~/Library/Application Support/reponews/state.json``
    Windows  ``%USERPROFILE%\AppData\Local\jwodder\reponews\state.json``
    =======  =================================================================

``api-url`` : URL
    The GraphQL endpoint to query; defaults to "https://api.github.com/graphql"

``activity`` : table
    A subtable describing what types of repository activity to fetch & track.
    This table may contain the following keys:

    ``issues`` : boolean
        Whether to report new issues in tracked repositories; defaults to true

    ``pull-requests`` : boolean
        Whether to report new pull requests in tracked repositories; defaults
        to true

    ``discussions`` : boolean
        Whether to report new `discussions`_ in tracked repositories; defaults
        to true

    ``releases`` : boolean
        Whether to report new releases in tracked repositories; defaults to
        true

    ``prereleases`` : boolean
        Whether to report new prereleases in tracked repositories; defaults to
        true.  This setting only has an effect when ``releases`` is true.

    ``drafts`` : boolean
        Whether to report new draft releases in tracked repositories; defaults
        to true.  This setting only has an effect when ``releases`` is true.

        Note that, if ``reponews`` sees a release while it's in a draft state
        (even if the draft is not reported), and then, on a later run, the
        release has been published, the release will not be reported on the
        later run, regardless of the value of ``drafts``.

    ``tags`` : boolean
        Whether to report new tags in tracked repositories; defaults to true

    ``released-tags`` : boolean
        This setting controls how to handle tags that are also made into
        releases when both tags and releases are being tracked.  If true, such
        tags are reported separately from the releases.  If false (the
        default), such tags are not reported.

    ``stars`` : boolean
        Whether to report new stargazers for tracked repositories; defaults to
        true

    ``forks`` : boolean
        Whether to report new forks of tracked repositories; defaults to true

    ``my-activity`` : boolean
        When false (the default), activity performed by the authenticated user
        is not reported.

    ``affiliated`` : table
        A subtable describing what types of repository activity to fetch &
        track for repositories affiliated with the authenticated user.  The
        table's keys are the same as the boolean keys of
        ``[reponews.activity]``.

    ``repo`` : table
        A subtable describing what types of repository activity to fetch &
        track for specific repositories or repositories belonging to a given
        user/organization.  The keys of the subtable must be of the form
        ``"owner/name"`` (for a specific repository) or ``"owner/*"`` (for all
        repositories belonging to a given user/organization), and the values
        must be subtables with the same boolean keys as
        ``[reponews.activity]``.

        By default, all repositories and repository owners listed as keys in
        ``[reponews.activity.repo]`` will be tracked by ``reponews`` just as if
        they were listed under ``reponews.repos.include`` (see below).  This
        can be disabled for a single key by setting ``include = false`` in the
        key's subtable.

    When determining the activity to fetch & track for a repository
    ``owner/name``, each setting is looked up in the relevant tables in the
    following order, from highest precedence to lowest precedence:

    1. ``[reponews.activity.repo."owner/name"]``
    2. ``[reponews.activity.repo."owner/*"]``
    3. ``[reponews.activity.affiliated]`` (if the repository is affiliated with
       the authenticated user)
    4. ``[reponews.activity]``

``repos`` : table
    A subtable describing what repositories to track.  This table may contain
    the following keys:

    ``affiliations`` : list of strings
        A list of repository affiliations describing which repositories
        associated with the authenticated user should be automatically tracked.
        The affiliations are ``"OWNER"`` (for tracking repositories that the
        user owns), ``"ORGANIZATION_MEMBER"`` (for tracking repositories
        belonging to an organization of which the user is a member), and
        ``"COLLABORATOR"`` (for tracking repositories to which the user has
        been added as a collaborator).  Unknown affiliations result in an
        error.  When ``affiliations`` is not specified, it defaults to all
        affiliation types.

    ``include`` : list of strings
        A list of repositories to track in addition to affiliated repositories.
        Repositories can be specified as either ``"owner/name"`` (for a
        specific repository) or ``"owner/*"`` (for all repositories belonging
        to a given user/organization).

    ``exclude`` : list of strings
        A list of repositories to exclude from tracking, specified the same way
        as for ``include``.  This option takes precedence over the
        ``affiliations`` and ``include`` settings.

.. _discussions: https://docs.github.com/en/discussions


Example Configuration
---------------------

.. code:: toml

    [reponews]
    recipient = "luser@example.com"

    sender = "RepoNews Bot <reponews@example.net>"

    # Fetch the GitHub access token from the "token.txt" file next to the
    # config file:
    auth-token-file = "token.txt"

    state-file = "~/.cache/reponews.json"

    [reponews.activity]
    # Don't report new issues or tags:
    issues = false
    tags = false

    [reponews.activity.affiliated]
    # Do report new issues for affiliated repositories:
    issues = true

    [reponews.activity.repo."pypa/*"]
    # Don't report forks of pypa/* repositories:
    forks = false
    # Don't track all pypa/* repositories; only track those we're affiliated
    # with and those listed under `reponews.repos.include`.
    #
    # Without this setting, the presence of `[reponews.activity.repo."pypa/*"]`
    # would cause reponews to track all repositories belonging to the pypa
    # organization.
    include = false

    [reponews.repos]
    affiliations = ["OWNER", "ORGANIZATION_MEMBER"]
    include = [
        "pypa/packaging",
        "pypa/pip",
        "pypa/setuptools",
        "some-user/*",
    ]
    exclude = [
        "some-user/boring-repo",
    ]


Sending E-Mail
==============

``reponews`` uses outgoing_ for sending e-mail, allowing it to handle multiple
sending methods like sendmail, SMTP, and more.  The `outgoing configuration`_
can be located in the ``reponews`` configuration file (as an ``[outgoing]``
table) or in ``outgoing``'s default configuration file.  See `outgoing's
documentation <https://outgoing.rtfd.io>`_ for more information.

.. _outgoing: https://github.com/jwodder/outgoing

.. _outgoing configuration:
   https://outgoing.readthedocs.io/en/latest/configuration.html
