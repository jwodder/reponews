v0.6.0 (2025-04-13)
-------------------
- Retry requests that fail due to connection, read, etc. errors

v0.5.1 (2025-03-29)
-------------------
- Support Python 3.13
- Fix a deprecation warning in Pydantic 2.11

v0.5.0 (2024-05-02)
-------------------
- Support platformdirs v4.0
- Migrated from setuptools to hatch
- Support configuring whether to report prereleases and/or draft releases

v0.4.0 (2023-10-31)
-------------------
- Support python-dotenv v1.0
- Use [`ghtoken`](https://github.com/jwodder/ghtoken) for looking up GitHub
  tokens
- Ensure that the state file is always read & written using UTF-8 encoding
- Always read the auth-token-file using UTF-8 encoding
- Explicitly depend on `click-loglevel`
- Support Python 3.12
- Correct the default Linux config file location listed in the README
- Set the `User-Agent` header in e-mails
- Update pydantic to v2.0
- Drop support for Python 3.7

v0.3.0 (2023-02-09)
-------------------
- Update `platformdirs` dependency to v3.  This is a **breaking** change on
  macOS, where the default configuration path changes from
  `~/Library/Preferences/reponews/config.toml` to `~/Library/Application
  Support/reponews/config.toml`.

v0.2.0 (2022-10-25)
-------------------
- Update minimum pydantic version to 1.9
- Retry GraphQL requests that fail with 5xx errors
- Support Python 3.11
- Use `tomllib` on Python 3.11

v0.1.1 (2022-01-02)
-------------------
- Support tomli 2.0

v0.1.0 (2022-01-02)
-------------------
Initial release
