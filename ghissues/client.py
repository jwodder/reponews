import json
from pathlib import Path
import requests
from .types import NewIssueEvent, NewPREvent, NewDiscussEvent, NewRepoEvent

PAGE_SIZE = 50

GITHUB_GRAPHQL_URL = 'https://api.github.com/graphql'

class GitHub:
    def __init__(self, token_file: Path):
        token = token_file.read_text().strip()
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"bearer {token}"

    def query(self, query, variables=None):
        r = self.s.post(GITHUB_GRAPHQL_URL, json={
            "query": query,
            "variables": variables or {},
        })
        if not r.ok or r.json().get("errors"):
            raise APIException(r)
        return r.json()

    def paginate(self, query, variables, conn_path):
        nodes = []
        while True:
            data = self.query(query, variables)
            conn = data
            for p in conn_path:
                conn = conn[p]
            nodes.extend(conn["nodes"])
            new_cursor = conn["pageInfo"]["endCursor"]
            if conn["pageInfo"]["hasNextPage"]:
                variables = {**variables, "cursor": new_cursor}
            else:
                return nodes, new_cursor

    def get_user_repos(self, user):
        q = '''
            query($user: String!, $page_size: Int!, $cursor: String) {
                user(login: $user) {
                    repositories(
                        ownerAffiliations: [OWNER, ORGANIZATION_MEMBER, COLLABORATOR],
                        orderBy: {field: NAME, direction: ASC},
                        first: $page_size,
                        after: $cursor
                    ) {
                        nodes {
                            id
                            nameWithOwner
                            createdAt
                            url
                        }
                        pageInfo {
                            endCursor
                            hasNextPage
                        }
                    }
                }
            }
        '''
        variables = {"user": user, "page_size": PAGE_SIZE}
        for node in self.paginate(
            q,
            variables,
            ('data', 'user', 'repositories'),
        )[0]:
            yield Repository(
                gh        = self,
                id        = node["id"],
                fullname  = node["nameWithOwner"],
                timestamp = node["createdAt"],
                url       = node["url"],
            )


class Repository:
    def __init__(self, gh, id, fullname, timestamp, url):
        self.gh = gh
        self.id = id
        self.fullname = fullname
        self.timestamp = timestamp
        self.url = url
        self.issues = IssueoidManager(self, 'issues', NewIssueEvent)
        self.prs = IssueoidManager(self, 'pullRequests', NewPREvent)
        self.discussions = IssueoidManager(self, 'discussions', NewDiscussEvent)
        self.new_event = NewRepoEvent(
            timestamp     = timestamp,
            repo_fullname = fullname,
            url           = url,
        )


class IssueoidManager:
    def __init__(self, repo, typename, event_class):
        self.repo = repo
        self.typename = typename
        self.event_class = event_class

    def get_new(self, cursor):
        q = '''
            query($repo_id: ID!, $page_size: Int!, $cursor: String) {
                node(id: $repo_id) {
                    ... on Repository {
                        %s (
                            orderBy: {field: CREATED_AT, direction: ASC},
                            first: $page_size,
                            after: $cursor
                        ) {
                            nodes {
                                author { login }
                                createdAt
                                number
                                title
                                url
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                }
            }
        ''' % (self.typename,)
        variables = {
            "repo_id": self.repo.id,
            "page_size": PAGE_SIZE,
            "cursor": cursor,
        }
        events = []
        nodes, new_cursor = self.repo.gh.paginate(
            q,
            variables,
            ('data', 'node', self.typename),
        )
        for node in nodes:
            events.append(self.event_class(
                repo_fullname = self.repo.fullname,
                timestamp     = node["createdAt"],
                number        = node["number"],
                title         = node["title"],
                author        = node["author"]["login"],
                url           = node["url"],
            ))
        return events, new_cursor

    def get_latest_cursor(self):
        q = '''
            query($repo_id: ID!) {
                node(id: $repo_id) {
                    ... on Repository {
                        %s (
                            orderBy: {field: CREATED_AT, direction: ASC},
                            last: 1
                        ) {
                            pageInfo {
                                endCursor
                            }
                        }
                    }
                }
            }
        ''' % (self.typename,)
        return self.repo.gh.query(q, {"repo_id": self.repo.id})\
            ["data"]["node"][self.typename]["pageInfo"]["endCursor"]


class APIException(Exception):
    def __init__(self, response):
        self.response = response

    def __str__(self):
        if self.response.ok:
            msg = 'GraphQL API error for URL: {0.url}\n'
        elif 400 <= self.response.status_code < 500:
            msg = '{0.status_code} Client Error: {0.reason} for URL: {0.url}\n'
        elif 500 <= self.response.status_code < 600:
            msg = '{0.status_code} Server Error: {0.reason} for URL: {0.url}\n'
        else:
            msg = '{0.status_code} Unknown Error: {0.reason} for URL: {0.url}\n'
        msg = msg.format(self.response)
        try:
            resp = self.response.json()
        except ValueError:
            msg += self.response.text
        else:
            msg += json.dumps(resp, sort_keys=True, indent=4)
        return msg
