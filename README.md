# Haroka site

Public source for https://haroka.github.io/ . Existing featured articles, talks, and series are curated in index.html.

`python3 scripts/update_note.py` fetches https://note.com/haroppe/rss and refreshes only the generated latest-six note block and assets/note-latest.json. Feed titles are escaped, article URLs must belong to haroppe, and invalid/empty responses preserve previous data. No AI API, paid service, dependency, or personal access token is used.

The standard Linux GitHub Actions workflow runs daily at **08:00 JST** (23:00 UTC), on main pushes, or manually. Scheduling can be delayed by GitHub. Only changed article data is committed. A scheduled run without differences does not deploy. On fetch failure it keeps the last successful articles. Pages publishes explicitly from the artifact in the same workflow; it does not rely on a bot commit starting another workflow. `source-commit.txt` identifies the published source commit.

Workflow permissions are limited by job: build writes changed public article files via its temporary GITHUB_TOKEN; deploy uses Pages write and a temporary OIDC token. No persistent credential or account-wide permission is added.

**GitHub inactivity limitation:** a public repository's scheduled workflows can be disabled after 60 days without repository activity. Monthly note posts normally create article commits; a longer pause can stop the schedule. After a long pause, open Actions → Sync note and deploy Pages → Enable workflow → Run workflow, or use `gh workflow enable site.yml` then `gh workflow run site.yml`. This implementation does not create dummy commits or add an extra privileged keepalive. See https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows .

Tests: `python3 -m unittest discover -s tests`.
