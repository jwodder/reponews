v0.4.0 (in development)
-----------------------
- Support python-dotenv v1.0
- Use [`ghtoken`](https://github.com/jwodder/ghtoken) for looking up GitHub
  tokens

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
