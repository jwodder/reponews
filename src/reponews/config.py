from __future__ import annotations
from collections import defaultdict
from email.headerregistry import Address as PyAddress
import json
import os
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Set, Tuple, Union
from ghrepo import GH_REPO_RGX, GH_USER_RGX
from mailbits import parse_address
from pydantic import BaseModel, Field, FilePath
from pydantic.validators import path_validator, str_validator
import tomli
from .types import Affiliation, IssueoidType, Repository
from .util import expanduser, get_default_state_file, mkalias

if sys.version_info[:2] >= (3, 8):
    from functools import cached_property
else:
    from backports.cached_property import cached_property

if TYPE_CHECKING:
    from pydantic.typing import CallableGenerator

    ExpandedPath = Path
    ExpandedFilePath = Path

else:

    class ExpandedPath(Path):
        @classmethod
        def __get_validators__(cls) -> CallableGenerator:
            yield path_validator
            yield expanduser

    class ExpandedFilePath(FilePath):
        @classmethod
        def __get_validators__(cls) -> CallableGenerator:
            yield path_validator
            yield expanduser
            yield from super().__get_validators__()


class Address(BaseModel):
    name: Optional[str]
    address: str

    @classmethod
    def __get_validators__(cls) -> CallableGenerator:
        yield str_validator
        yield cls._parse

    @classmethod
    def _parse(cls, value: str) -> Address:
        addr = parse_address(value)
        return cls(name=addr.display_name or None, address=addr.addr_spec)

    def as_py_address(self) -> PyAddress:
        return PyAddress(self.name or "", addr_spec=self.address)


class RepoSpec(BaseModel):
    owner: str
    name: Optional[str]

    @classmethod
    def __get_validators__(cls) -> CallableGenerator:
        yield str_validator
        yield cls._parse

    @classmethod
    def _parse(cls, value: str) -> RepoSpec:
        m = re.fullmatch(
            fr"(?P<owner>{GH_USER_RGX})/(?:\*|(?P<name>{GH_REPO_RGX}))", value
        )
        if m:
            return cls(owner=m["owner"], name=m["name"])
        else:
            raise ValueError(f"Invalid repo spec: {value!r}")


class BaseConfig(BaseModel):
    class Config:
        alias_generator = mkalias
        extra = "forbid"

        # <https://github.com/samuelcolvin/pydantic/issues/1241>
        arbitrary_types_allowed = True
        keep_untouched = (cached_property,)


class ActivityConfig(BaseConfig):
    issues: bool = True
    prs: bool = True
    discussions: bool = True
    my_activity: bool = False


class ReposConfig(BaseConfig):
    affiliations: List[Affiliation] = Field(default_factory=lambda: list(Affiliation))
    include: List[RepoSpec] = Field(default_factory=list)
    exclude: List[RepoSpec] = Field(default_factory=list)


class RepoInclusions(BaseModel):
    included_owners: Set[str] = Field(default_factory=set)
    excluded_owners: Set[str] = Field(default_factory=set)
    included_repos: Dict[str, Set[str]] = Field(
        default_factory=lambda: defaultdict(set)
    )
    excluded_repos: Dict[str, Set[str]] = Field(
        default_factory=lambda: defaultdict(set)
    )

    @classmethod
    def from_repos_config(cls, repos_config: ReposConfig) -> RepoInclusions:
        rinc = cls()
        for rs in repos_config.include:
            if rs.name is None:
                rinc.included_owners.add(rs.owner)
            else:
                rinc.included_repos[rs.owner].add(rs.name)
        for rs in repos_config.exclude:
            if rs.name is None:
                rinc.excluded_owners.add(rs.owner)
                rinc.included_owners.discard(rs.owner)
                rinc.included_repos.pop(rs.owner, None)
            else:
                rinc.excluded_repos[rs.owner].add(rs.name)
                rinc.included_repos[rs.owner].discard(rs.name)
        return rinc

    def get_included_repo_owners(self) -> List[str]:
        return sorted(self.included_owners)

    def get_included_repos(self) -> List[Tuple[str, str]]:
        return [
            (owner, n)
            for owner, names in sorted(self.included_repos.items())
            if owner not in self.included_owners
            for n in sorted(names)
        ]

    def is_repo_excluded(self, repo: Repository) -> bool:
        return (
            repo.owner in self.excluded_owners
            or repo.name in self.excluded_repos[repo.owner]
        )


class Configuration(BaseConfig):
    recipient: Address
    sender: Optional[Address] = None
    subject: str = "New issues on your GitHub repositories"
    auth_token: Optional[str] = None
    auth_token_file: Optional[ExpandedFilePath] = None
    # The default is implemented as a factory in order to make it easy to test
    # with a fake $HOME:
    state_file: ExpandedPath = Field(default_factory=get_default_state_file)
    api_url: str = "https://api.github.com/graphql"
    activity: ActivityConfig = Field(default_factory=ActivityConfig)
    repos: ReposConfig = Field(default_factory=ReposConfig)

    @classmethod
    def from_toml_file(cls, filepath: Union[str, Path]) -> Configuration:
        with open(filepath, "rb") as fp:
            data = tomli.load(fp).get("reponews", {})
        return cls.parse_obj(data)

    def get_auth_token(self) -> str:
        if self.auth_token is not None:
            return self.auth_token
        elif self.auth_token_file is not None:
            return self.auth_token_file.read_text().strip()
        elif os.environ.get("GITHUB_TOKEN"):
            return os.environ["GITHUB_TOKEN"]
        elif os.environ.get("GH_TOKEN"):
            return os.environ["GH_TOKEN"]
        else:
            ### TODO: Use a different/custom exception type?
            raise RuntimeError(
                "GitHub OAuth token not set.  Specify in config file or via"
                " GITHUB_TOKEN or GH_TOKEN environment variable."
            )

    def active_issueoid_types(self) -> Iterator[IssueoidType]:
        if self.activity.issues:
            yield IssueoidType.ISSUE
        if self.activity.prs:
            yield IssueoidType.PR
        if self.activity.discussions:
            yield IssueoidType.DISCUSSION

    @cached_property
    def inclusions(self) -> RepoInclusions:
        return RepoInclusions.from_repos_config(self.repos)

    def get_included_repo_owners(self) -> List[str]:
        return self.inclusions.get_included_repo_owners()

    def get_included_repos(self) -> List[Tuple[str, str]]:
        return self.inclusions.get_included_repos()

    def is_repo_excluded(self, repo: Repository) -> bool:
        return self.inclusions.is_repo_excluded(repo)

    def for_json(self) -> Any:
        return json.loads(self.json())