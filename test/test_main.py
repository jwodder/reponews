from __future__ import annotations
from collections.abc import Iterator
from email import message_from_string, policy
from email.message import EmailMessage
from functools import partial
import json
import logging
from pathlib import Path
from shutil import copytree
from traceback import format_exception
from types import TracebackType
from typing import Dict, List, Optional, Union, cast
from unittest.mock import ANY
from click.testing import CliRunner, Result
from mailbits import email2dict
from pydantic import BaseModel
import pytest
from pytest_mock import MockerFixture
from reponews.__main__ import main
from reponews.types import (
    ActivityType,
    Affiliation,
    CursorDict,
    NewDiscussionEvent,
    NewForkEvent,
    NewIssueEvent,
    NewPREvent,
    NewReleaseEvent,
    NewStarEvent,
    NewTagEvent,
    RepoActivity,
    Repository,
)
from reponews.util import MAIL_USER_AGENT, NotFoundError

MOCK_DIR = Path(__file__).with_name("data") / "mock"


class ActivityQuery(BaseModel):
    activity_types: List[ActivityType]
    cursors_in: CursorDict
    events: List[
        Union[
            NewDiscussionEvent,
            NewForkEvent,
            NewIssueEvent,
            NewPREvent,
            NewReleaseEvent,
            NewStarEvent,
            NewTagEvent,
        ]
    ]
    cursors_out: CursorDict


class SessionData(BaseModel):
    affiliated: List[Repository]
    owners: Dict[str, Optional[List[Repository]]]
    repos: Dict[str, Optional[Repository]]
    activity: Dict[str, ActivityQuery]


class MockClient:
    def __init__(self, api_url: str, token: str, querying: bool = True) -> None:
        assert api_url == "https://test.nil/api"
        assert token == "1234567890"
        with (MOCK_DIR / "session-data.json").open() as fp:
            self.data = SessionData.model_validate(json.load(fp))
        self.querying = querying

    def __enter__(self) -> MockClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is None and self.querying:
            assert not self.data.owners, "Not all owners queried"
            assert not self.data.repos, "Not all repositories queried"
            assert not self.data.activity, "Not all activity queried"

    def get_affiliated_repos(
        self, affiliations: list[Affiliation]
    ) -> Iterator[Repository]:
        assert affiliations == [Affiliation.OWNER, Affiliation.COLLABORATOR]
        return iter(self.data.affiliated)

    def get_owner_repos(self, owner: str) -> Iterator[Repository]:
        assert owner in self.data.owners
        repos = self.data.owners.pop(owner)
        if repos is None:
            raise NotFoundError(f"No such repository owner: {owner}")
        return iter(repos)

    def get_repo(self, owner: str, name: str) -> Repository:
        fullname = f"{owner}/{name}"
        assert fullname in self.data.repos
        r = self.data.repos.pop(fullname)
        if r is None:
            raise NotFoundError(f"No such repository: {fullname}")
        return r

    def get_new_repo_activity(
        self, repo: Repository, types: list[ActivityType], cursors: CursorDict
    ) -> tuple[list[RepoActivity], CursorDict]:
        fullname = repo.nameWithOwner
        assert fullname in self.data.activity
        aq = self.data.activity.pop(fullname)
        assert aq.activity_types == types
        assert aq.cursors_in == cursors
        return (cast(List[RepoActivity], aq.events), aq.cursors_out)


MSG_SPEC = {
    "unixfrom": None,
    "headers": {
        "subject": "Your Repo News is here!",
        "from": [
            {
                "display_name": "RepoNews",
                "address": "reponews@example.com",
            },
        ],
        "to": [
            {
                "display_name": "",
                "address": "viewer@example.org",
            }
        ],
        "content-type": {
            "content_type": "text/plain",
            "params": {},
        },
        "user-agent": [MAIL_USER_AGENT],
    },
    "preamble": ANY,
    "content": (MOCK_DIR / "body.txt").read_text(),
    "epilogue": ANY,
}


def show_result(r: Result) -> str:
    if r.exception is not None:
        assert isinstance(r.exc_info, tuple)
        return "".join(format_exception(*r.exc_info))
    else:
        return r.output


def assert_json_eq(p1: Path, p2: Path) -> None:
    assert json.loads(p1.read_text()) == json.loads(p2.read_text())


def test_dump_repos(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("reponews.client.Client", partial(MockClient, querying=False))
    copytree(MOCK_DIR / "home", tmp_path / "home")
    r = CliRunner().invoke(
        main,
        ["--config", str(tmp_path / "home" / "config.toml"), "--dump-repos"],
        standalone_mode=False,
    )
    assert r.exit_code == 0, show_result(r)
    assert r.output == (MOCK_DIR / "dump-repos.txt").read_text()
    assert (
        "reponews",
        logging.WARNING,
        "User user-not-found does not exist!",
    ) in caplog.record_tuples
    assert (
        "reponews",
        logging.WARNING,
        "Repository luser/repo-not-found does not exist!",
    ) in caplog.record_tuples
    assert_json_eq(tmp_path / "home" / "state.json", MOCK_DIR / "home" / "state.json")


@pytest.mark.parametrize("save", [True, False])
def test_print_body(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    save: bool,
) -> None:
    monkeypatch.setattr("reponews.client.Client", MockClient)
    copytree(MOCK_DIR / "home", tmp_path / "home")
    args = ["--config", str(tmp_path / "home" / "config.toml"), "--print-body"]
    if not save:
        args.append("--no-save")
    r = CliRunner().invoke(main, args, standalone_mode=False)
    assert r.exit_code == 0, show_result(r)
    assert r.output == (MOCK_DIR / "body.txt").read_text()
    assert (
        "reponews",
        logging.WARNING,
        "User user-not-found does not exist!",
    ) in caplog.record_tuples
    assert (
        "reponews",
        logging.WARNING,
        "Repository luser/repo-not-found does not exist!",
    ) in caplog.record_tuples
    if save:
        assert_json_eq(tmp_path / "home" / "state.json", MOCK_DIR / "new-state.json")
    else:
        assert_json_eq(
            tmp_path / "home" / "state.json", MOCK_DIR / "home" / "state.json"
        )


@pytest.mark.parametrize("save", [True, False])
def test_print(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    save: bool,
) -> None:
    monkeypatch.setattr("reponews.client.Client", MockClient)
    copytree(MOCK_DIR / "home", tmp_path / "home")
    args = ["--config", str(tmp_path / "home" / "config.toml"), "--print"]
    if not save:
        args.append("--no-save")
    r = CliRunner().invoke(main, args, standalone_mode=False)
    assert r.exit_code == 0, show_result(r)
    # <https://github.com/python/typeshed/issues/13273>
    msg = message_from_string(r.output, policy=policy.default)  # type: ignore[arg-type]
    assert email2dict(msg) == MSG_SPEC
    assert (
        "reponews",
        logging.WARNING,
        "User user-not-found does not exist!",
    ) in caplog.record_tuples
    assert (
        "reponews",
        logging.WARNING,
        "Repository luser/repo-not-found does not exist!",
    ) in caplog.record_tuples
    if save:
        assert_json_eq(tmp_path / "home" / "state.json", MOCK_DIR / "new-state.json")
    else:
        assert_json_eq(
            tmp_path / "home" / "state.json", MOCK_DIR / "home" / "state.json"
        )


@pytest.mark.parametrize("save", [True, False])
def test_send(
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    save: bool,
) -> None:
    monkeypatch.setattr("reponews.client.Client", MockClient)
    m = mocker.patch("outgoing.senders.null.NullSender", autospec=True)
    copytree(MOCK_DIR / "home", tmp_path / "home")
    args = ["--config", str(tmp_path / "home" / "config.toml")]
    if not save:
        args.append("--no-save")
    r = CliRunner().invoke(main, args, standalone_mode=False)
    assert r.exit_code == 0, show_result(r)
    assert r.output == ""
    m.assert_called_once_with(
        method="null", configpath=tmp_path / "home" / "config.toml"
    )
    instance = m.return_value
    assert instance.send.call_count == 1
    sent = instance.send.call_args[0][0]
    assert isinstance(sent, EmailMessage)
    assert email2dict(sent) == MSG_SPEC
    assert (
        "reponews",
        logging.WARNING,
        "User user-not-found does not exist!",
    ) in caplog.record_tuples
    assert (
        "reponews",
        logging.WARNING,
        "Repository luser/repo-not-found does not exist!",
    ) in caplog.record_tuples
    if save:
        assert_json_eq(tmp_path / "home" / "state.json", MOCK_DIR / "new-state.json")
    else:
        assert_json_eq(
            tmp_path / "home" / "state.json", MOCK_DIR / "home" / "state.json"
        )
