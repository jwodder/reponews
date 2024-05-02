from __future__ import annotations
import json
from operator import attrgetter
from os.path import expanduser
from pathlib import Path
from typing import List, Tuple
import ghtoken
from pydantic import BaseModel, ValidationError
import pytest
from pytest_mock import MockerFixture
from reponews.config import ActivityPrefs, Configuration
from reponews.types import ActivityType, Repository, User
from reponews.util import UserError, get_default_state_file

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
    assert config.model_dump(mode="json") == expected


@pytest.mark.parametrize(
    "tomlfile",
    sorted((DATA_DIR / "bad-config").glob("*.toml")),
    ids=attrgetter("name"),
)
def test_parse_bad_config(tomlfile: Path) -> None:
    with pytest.raises(ValidationError):
        Configuration.from_toml_file(tomlfile)


class InclusionCase(BaseModel):
    included_owners: List[str]
    included_repos: List[Tuple[str, str]]
    not_excluded_repos: List[Tuple[str, str]]
    excluded_repos: List[Tuple[str, str]]


@pytest.mark.parametrize(
    "tomlfile",
    sorted((DATA_DIR / "inclusions").glob("*.toml")),
    ids=attrgetter("name"),
)
def test_inclusions(tomlfile: Path) -> None:
    config = Configuration.from_toml_file(DATA_DIR / "inclusions" / tomlfile)
    with tomlfile.with_suffix(".json").open() as fp:
        expected = InclusionCase.model_validate(json.load(fp))
    assert config.get_included_repo_owners() == expected.included_owners
    assert config.get_included_repos() == expected.included_repos
    for owner, name in expected.not_excluded_repos:
        assert not config.is_repo_excluded(mkrepo(owner, name))
    for owner, name in expected.excluded_repos:
        assert config.is_repo_excluded(mkrepo(owner, name))


@pytest.mark.parametrize(
    "tomlfile,repo,is_affiliated,prefs",
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=False,
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
                prereleases=True,
                drafts=False,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
                prereleases=True,
                drafts=True,
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
    tomlfile: str, repo: Repository, is_affiliated: bool, prefs: ActivityPrefs
) -> None:
    config = Configuration.from_toml_file(DATA_DIR / "config" / tomlfile)
    assert config.get_repo_activity_prefs(repo, is_affiliated) == prefs


@pytest.mark.parametrize(
    "prefs,types",
    [
        (
            ActivityPrefs(
                issues=True,
                pull_requests=True,
                discussions=True,
                releases=True,
                prereleases=True,
                drafts=True,
                tags=True,
                released_tags=False,
                stars=True,
                forks=True,
                my_activity=False,
            ),
            [
                ActivityType.ISSUE,
                ActivityType.PR,
                ActivityType.DISCUSSION,
                ActivityType.RELEASE,
                ActivityType.TAG,
                ActivityType.STAR,
                ActivityType.FORK,
            ],
        ),
        (
            ActivityPrefs(
                issues=False,
                pull_requests=False,
                discussions=False,
                releases=False,
                prereleases=True,
                drafts=True,
                tags=False,
                released_tags=True,
                stars=False,
                forks=False,
                my_activity=True,
            ),
            [],
        ),
        (
            ActivityPrefs(
                issues=True,
                pull_requests=True,
                discussions=True,
                releases=True,
                prereleases=True,
                drafts=True,
                tags=False,
                released_tags=True,
                stars=False,
                forks=False,
                my_activity=True,
            ),
            [
                ActivityType.ISSUE,
                ActivityType.PR,
                ActivityType.DISCUSSION,
                ActivityType.RELEASE,
            ],
        ),
    ],
)
def test_get_activity_types(prefs: ActivityPrefs, types: list[ActivityType]) -> None:
    assert prefs.get_activity_types() == types


def test_get_auth_token_explicit(
    monkeypatch: pytest.MonkeyPatch, tmp_home: Path
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "QWERTY")
    (tmp_home / "token.txt").write_text("abcdef\n")
    config = Configuration(
        auth_token="123456",
        auth_token_file="~/token.txt",
    )
    assert config.get_auth_token() == "123456"


def test_get_auth_token_file(monkeypatch: pytest.MonkeyPatch, tmp_home: Path) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "QWERTY")
    (tmp_home / "token.txt").write_text("abcdef\n")
    config = Configuration(auth_token_file="~/token.txt")
    assert config.get_auth_token() == "abcdef"


@pytest.mark.usefixtures("tmp_home")
def test_get_auth_token_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "QWERTY")
    config = Configuration(auth_token_file="~/token.txt")
    with pytest.raises(FileNotFoundError):
        config.get_auth_token()


def test_get_auth_token_ghtoken(mocker: MockerFixture, tmp_home: Path) -> None:
    m = mocker.patch("ghtoken.get_ghtoken", return_value="gh_token")
    (tmp_home / "token.txt").write_text("abcdef\n")
    config = Configuration()
    assert config.get_auth_token() == "gh_token"
    m.assert_called_once_with(dotenv=False)


def test_get_auth_token_notset(mocker: MockerFixture, tmp_home: Path) -> None:
    m = mocker.patch("ghtoken.get_ghtoken", side_effect=ghtoken.GHTokenNotFound())
    (tmp_home / "token.txt").write_text("abcdef\n")
    config = Configuration()
    with pytest.raises(UserError) as excinfo:
        config.get_auth_token()
    assert str(excinfo.value) == (
        "GitHub access token not found.  Set via config file, GH_TOKEN,"
        " GITHUB_TOKEN, gh, hub, or hub.oauthtoken."
    )
    m.assert_called_once_with(dotenv=False)
