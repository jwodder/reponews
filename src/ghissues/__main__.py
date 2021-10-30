from __future__ import annotations
import json
from operator import attrgetter
from pathlib import Path
import sys
import time
from typing import TYPE_CHECKING, Dict, List, Optional, cast
from eletter import compose
from mailbits import parse_address
from outgoing import from_config_file
from .client import GitHub
from .types import Event, RepoRemovedEvent

USER = "jwodder"
RECIPIENT = "REDACTED"
SUBJECT = "New issues on your GitHub repositories"
SKIP_SELF_REPORTED = True

TOKEN_FILE = Path.home() / ".github"
STATE_FILE = Path.home() / ".varlib" / "ghissues.json"

if TYPE_CHECKING:
    if sys.version_info[:2] >= (3, 8):
        from typing import TypedDict
    else:
        from typing_extensions import TypedDict

    class RepoState(TypedDict, total=False):
        fullname: str
        issues: Optional[str]
        prs: Optional[str]
        discussions: Optional[str]


def main() -> None:
    gh = GitHub(TOKEN_FILE)
    try:
        with STATE_FILE.open() as fp:
            state = json.load(fp)
    except FileNotFoundError:
        state = {}
    events: List[Event] = []
    new_state: Dict[str, RepoState] = {}
    for repo in gh.get_user_repos(USER):
        try:
            repo_state = cast(RepoState, state.pop(repo.id))
        except KeyError:
            repo_state = {
                "issues": repo.issues.get_latest_cursor(),
                "prs": repo.prs.get_latest_cursor(),
                "discussions": repo.discussions.get_latest_cursor(),
            }
            events.append(repo.new_event)
        else:
            ### TODO: Cut down on code duplication here:
            issues, new_cursor = repo.issues.get_new(repo_state["issues"])
            if new_cursor is not None:
                repo_state["issues"] = new_cursor
            events.extend(
                i for i in issues if i.author != USER or not SKIP_SELF_REPORTED
            )
            prs, new_cursor = repo.prs.get_new(repo_state["prs"])
            if new_cursor is not None:
                repo_state["prs"] = new_cursor
            events.extend(p for p in prs if p.author != USER or not SKIP_SELF_REPORTED)
            try:
                discurse = repo_state["discussions"]
            except KeyError:
                discurse = repo_state[
                    "discussions"
                ] = repo.discussions.get_latest_cursor()
            discs, new_cursor = repo.discussions.get_new(discurse)
            if new_cursor is not None:
                repo_state["discussions"] = new_cursor
            events.extend(
                d for d in discs if d.author != USER or not SKIP_SELF_REPORTED
            )
        repo_state["fullname"] = repo.fullname
        new_state[repo.id] = repo_state
    for repo_state in state.values():
        events.append(
            RepoRemovedEvent(
                timestamp=nowstamp(),
                repo_fullname=repo_state["fullname"],
            )
        )
    events.sort(key=attrgetter("timestamp"))
    if events:
        report_events(events)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(new_state))


def report_events(events: List[Event]) -> None:
    # print('\n\n'.join(map(str, events)))
    msg = compose(
        to=[parse_address(RECIPIENT)],
        subject=SUBJECT,
        text="\n\n".join(map(str, events)),
    )
    with from_config_file() as sender:
        sender.send(msg)


def nowstamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    main()
