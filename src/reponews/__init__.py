"""
Send e-mails about new events on your GitHub repositories

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

Visit <https://github.com/jwodder/reponews> for more information.
"""

__version__ = "0.6.0"
__author__ = "John Thorvald Wodder II"
__author_email__ = "reponews@varonathe.org"
__license__ = "MIT"
__url__ = "https://github.com/jwodder/reponews"
