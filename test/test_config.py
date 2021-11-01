from os.path import expanduser
from pathlib import Path
from typing import Any, List, Tuple
import pytest
from reponews.config import Configuration, ReposConfig
from reponews.types import Repository
from reponews.util import get_default_state_file
from testlib import filecases


def mkrepo(owner: str, name: str) -> Repository:
    return Repository(
        id="1234",
        owner=owner,
        name=name,
        fullname=f"{owner}/{name}",
        url=f"https://github.com/{owner}/{name}",
        description="A repository",
        descriptionHTML="A repository",
    )


@pytest.mark.parametrize("tomlfile,expected", filecases("config", "*.toml"))
def test_parse_config(tmp_home: Path, tomlfile: Path, expected: Any) -> None:
    (tmp_home / ".github").touch()
    config = Configuration.from_toml_file(tomlfile)
    if expected["state_file"] is None:
        expected["state_file"] = get_default_state_file()
    for key in ("auth_token_file", "state_file"):
        if expected[key] is not None:
            expected[key] = expanduser(expected[key])
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
