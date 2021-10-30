from email.message import EmailMessage
import json
from pathlib import Path
import subprocess
import time
from .client import GitHub
from .types import RepoRemovedEvent

USER = "jwodder"
RECIPIENT = "REDACTED"
SUBJECT = "New issues on your GitHub repositories"
SKIP_SELF_REPORTED = True

TOKEN_FILE = Path.home() / ".github"
STATE_FILE = Path.home() / ".varlib" / "ghissues.json"


def main():
    gh = GitHub(TOKEN_FILE)
    try:
        with STATE_FILE.open() as fp:
            state = json.load(fp)
    except FileNotFoundError:
        state = {}
    events = []
    new_state = {}
    for repo in gh.get_user_repos(USER):
        try:
            repo_state = state.pop(repo.id)
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
    events.sort()
    if events:
        report_events(events)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(new_state))


def report_events(events):
    # print('\n\n'.join(map(str, events)))
    msg = EmailMessage()
    msg["Subject"] = SUBJECT
    msg["To"] = RECIPIENT
    msg.set_content("\n\n".join(map(str, events)))
    subprocess.run(["sendmail", "-i", "-t"], input=bytes(msg), check=True)


def nowstamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    main()
