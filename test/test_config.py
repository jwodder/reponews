import json
from operator import attrgetter
from os.path import expanduser
from pathlib import Path
from typing import List, Tuple
import pytest
from reponews.config import ActivityPrefs, Configuration, ReposConfig
from reponews.types import Repository, User
from reponews.util import get_default_state_file

DATA_DIR = Path(__file__).with_name("data")


def mkrepo(owner: str, name: str) -> Repository:
    return Repository(
        id="1234",
        owner=User(login=owner, url=f"https://github.com/{owner}"),
        name=name,
        nameWithOwner=f"{owner}/{name}",
        url=f"https://github.com/{owner}/{name}",
        description="A repository",
        descriptionHTML="A repository",
    )


@pytest.mark.parametrize(
    "tomlfile",
    sorted((DATA_DIR / "config").glob("*.toml")),
    ids=attrgetter("name"),
)
@pytest.mark.usefixtures("tmp_home")
def test_parse_config(tomlfile: Path) -> None:
    config = Configuration.from_toml_file(tomlfile)
    with tomlfile.with_suffix(".json").open() as fp:
        expected = json.load(fp)
    if expected["state_file"] is None:
        expected["state_file"] = get_default_state_file()
    for key in ("auth_token_file", "state_file"):
        if expected[key] is not None:
            expected[key] = expanduser(expected[key]).format(config=tomlfile.parent)
    assert config.for_json() == expected


@pytest.mark.parametrize(
    "repos_config,included_owners,included_repos,not_excluded_repos,excluded_repos",
    [
        (ReposConfig(), [], [], [mkrepo("owner", "name")], []),
        (
            ReposConfig(include=["owner/*", "owner/name", "my/repo"]),
            ["owner"],
            [("my", "repo")],
            [
                mkrepo("owner", "name"),
                mkrepo("owner", "project"),
                mkrepo("my", "repo"),
                mkrepo("your", "project"),
            ],
            [],
        ),
        (
            ReposConfig(include=["owner/*", "me/*"], exclude=["owner/name", "me/*"]),
            ["owner"],
            [],
            [mkrepo("owner", "project"), mkrepo("your", "project")],
            [mkrepo("owner", "name"), mkrepo("me", "repo")],
        ),
        (
            ReposConfig(
                include=["owner/*", "me/repo", "your/hobby"],
                exclude=["owner/name", "me/*", "your/widget"],
            ),
            ["owner"],
            [("your", "hobby")],
            [
                mkrepo("owner", "project"),
                mkrepo("your", "hobby"),
                mkrepo("your", "project"),
            ],
            [
                mkrepo("owner", "name"),
                mkrepo("me", "repo"),
                mkrepo("me", "project"),
                mkrepo("your", "widget"),
            ],
        ),
    ],
)
def test_inclusions(
    repos_config: ReposConfig,
    included_owners: List[str],
    included_repos: List[Tuple[str, str]],
    not_excluded_repos: List[Repository],
    excluded_repos: List[Repository],
) -> None:
    config = Configuration(recipient="me@here.there", repos=repos_config)
    assert config.get_included_repo_owners() == included_owners
    assert config.get_included_repos() == included_repos
    for repo in not_excluded_repos:
        assert not config.is_repo_excluded(repo)
    for repo in excluded_repos:
        assert config.is_repo_excluded(repo)


@pytest.mark.parametrize(
    "cfgname,repo,is_affiliated,prefs",
    [
        (
            "empty.toml",
            mkrepo("owner", "repo"),
            True,
            ActivityPrefs(
                issues=True,
                pull_requests=True,
                discussions=True,
                releases=True,
                tags=True,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=False,
            ),
        ),
        (
            "empty.toml",
            mkrepo("owner", "repo"),
            False,
            ActivityPrefs(
                issues=True,
                pull_requests=True,
                discussions=True,
                releases=True,
                tags=True,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=False,
            ),
        ),
        (
            "full.toml",
            mkrepo("owner", "repo"),
            True,
            ActivityPrefs(
                issues=False,
                pull_requests=False,
                discussions=True,
                releases=True,
                tags=True,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=True,
            ),
        ),
        (
            "full.toml",
            mkrepo("owner", "repo"),
            False,
            ActivityPrefs(
                issues=False,
                pull_requests=False,
                discussions=True,
                releases=True,
                tags=True,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=True,
            ),
        ),
        (
            "repo-activity01.toml",
            mkrepo("luser", "repo"),
            True,
            ActivityPrefs(
                issues=False,
                pull_requests=False,
                discussions=True,
                releases=True,
                tags=True,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=False,
            ),
        ),
        (
            "repo-activity01.toml",
            mkrepo("luser", "repo"),
            False,
            ActivityPrefs(
                issues=True,
                pull_requests=True,
                discussions=True,
                releases=True,
                tags=True,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=False,
            ),
        ),
        (
            "repo-activity01.toml",
            mkrepo("owner", "project"),
            False,
            ActivityPrefs(
                issues=True,
                pull_requests=True,
                discussions=True,
                releases=True,
                tags=False,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=True,
            ),
        ),
        (
            "repo-activity01.toml",
            mkrepo("owner", "repo"),
            False,
            ActivityPrefs(
                issues=True,
                pull_requests=True,
                discussions=True,
                releases=False,
                tags=False,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=False,
            ),
        ),
        (
            "repo-activity01.toml",
            mkrepo("owner", "repo"),
            True,
            ActivityPrefs(
                issues=False,
                pull_requests=False,
                discussions=True,
                releases=False,
                tags=False,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=False,
            ),
        ),
        (
            "repo-activity02.toml",
            mkrepo("luser", "repo"),
            True,
            ActivityPrefs(
                issues=True,
                pull_requests=False,
                discussions=False,
                releases=True,
                tags=True,
                released_tags=False,
                stars=False,
                forks=False,
                my_activity=False,
            ),
        ),
        (
            "repo-activity02.toml",
            mkrepo("luser", "repo"),
            False,
            ActivityPrefs(
                issues=False,
                pull_requests=True,
                discussions=False,
                releases=True,
                tags=True,
                released_tags=False,
                stars=False,
                forks=False,
                my_activity=False,
            ),
        ),
        (
            "repo-activity02.toml",
            mkrepo("owner", "project"),
            False,
            ActivityPrefs(
                issues=False,
                pull_requests=True,
                discussions=False,
                releases=True,
                tags=False,
                released_tags=False,
                stars=True,
                forks=False,
                my_activity=True,
            ),
        ),
        (
            "repo-activity02.toml",
            mkrepo("owner", "repo"),
            False,
            ActivityPrefs(
                issues=False,
                pull_requests=True,
                discussions=False,
                releases=False,
                tags=False,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=False,
            ),
        ),
        (
            "repo-activity02.toml",
            mkrepo("owner", "repo"),
            True,
            ActivityPrefs(
                issues=True,
                pull_requests=False,
                discussions=False,
                releases=False,
                tags=False,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=False,
            ),
        ),
        (
            "yestags.toml",
            mkrepo("owner", "repo"),
            True,
            ActivityPrefs(
                issues=True,
                pull_requests=True,
                discussions=True,
                releases=True,
                tags=True,
                released_tags=True,
                stars=True,
                forks=True,
                my_activity=False,
            ),
        ),
        (
            "yestags.toml",
            mkrepo("owner", "repo"),
            False,
            ActivityPrefs(
                issues=True,
                pull_requests=True,
                discussions=True,
                releases=True,
                tags=True,
                released_tags=True,
                stars=True,
                forks=True,
                my_activity=False,
            ),
        ),
    ],
)
def test_get_repo_activity_prefs(
    cfgname: str, repo: Repository, is_affiliated: bool, prefs: ActivityPrefs
) -> None:
    config = Configuration.from_toml_file(DATA_DIR / "config" / cfgname)
    assert config.get_repo_activity_prefs(repo, is_affiliated) == prefs
