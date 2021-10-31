from __future__ import annotations
from email.headerregistry import Address as PyAddress
import json
import os
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Union
from ghrepo import GH_REPO_RGX, GH_USER_RGX
from mailbits import parse_address
from pydantic import BaseModel, Field, FilePath
from pydantic.validators import path_validator, str_validator
import tomli
from .util import Affiliation, IssueoidType, expanduser, get_default_state_file, mkalias

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


class AliasedBase(BaseModel):
    class Config:
        alias_generator = mkalias
        extra = "forbid"


class ActivityConfig(AliasedBase):
    new_issues: bool = True
    new_prs: bool = True
    new_discussions: bool = True
    my_activity: bool = False


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


class ReposConfig(AliasedBase):
    affiliations: List[Affiliation] = Field(default_factory=lambda: list(Affiliation))
    include: List[RepoSpec] = Field(default_factory=list)
    exclude: List[RepoSpec] = Field(default_factory=list)


class Configuration(AliasedBase):
    recipient: Address
    sender: Optional[Address] = None
    subject: str = "New issues on your GitHub repositories"
    github_token: Optional[str] = None
    github_token_file: Optional[ExpandedFilePath] = None
    # The default is implemented as a factory in order to make it easy to test
    # with a fake $HOME:
    state_file: ExpandedPath = Field(default_factory=get_default_state_file)
    api_url: str = "https://api.github.com/graphql"
    activity: ActivityConfig = Field(default_factory=ActivityConfig)
    repos: ReposConfig = Field(default_factory=ReposConfig)

    @classmethod
    def from_toml_file(cls, filepath: Union[str, Path]) -> Configuration:
        with open(filepath, "rb") as fp:
            data = tomli.load(fp).get("ghissues", {})
        return cls.parse_obj(data)

    def get_github_token(self) -> str:
        if self.github_token is not None:
            return self.github_token
        elif self.github_token_file is not None:
            return self.github_token_file.read_text().strip()
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
        if self.activity.new_issues:
            yield IssueoidType.ISSUE
        if self.activity.new_prs:
            yield IssueoidType.PR
        if self.activity.new_discussions:
            yield IssueoidType.DISCUSSION

    def for_json(self) -> Any:
        return json.loads(self.json())
