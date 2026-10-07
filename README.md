# Haroka site

Public source for https://haroka.github.io/ . Existing featured articles, talks, and series are curated in index.html.

`python3 scripts/update_note.py` fetches https://note.com/haroppe/rss and refreshes only the generated latest-six note block and assets/note-latest.json. Feed titles are escaped, article URLs must belong to haroppe, and invalid/empty responses preserve previous data. No AI API, paid service, dependency, or personal access token is used.

The standard Linux GitHub Actions workflow runs daily at **08:00 JST** (23:00 UTC), on main pushes, or manually. Scheduling can be delayed by GitHub. Only changed article data is committed. A scheduled run without differences does not deploy. On fetch failure it keeps the last successful articles. Pages publishes explicitly from the artifact in the same workflow; it does not rely on a bot commit starting another workflow. `source-commit.txt` identifies the published source commit.

Workflow permissions are limited by job: build writes changed public article files via its temporary GITHUB_TOKEN; deploy uses Pages write and a temporary OIDC token. No persistent credential or account-wide permission is added.

**GitHub inactivity limitation:** a public repository's scheduled workflows can be disabled after 60 days without repository activity. Monthly note posts normally create article commits; a longer pause can stop the schedule. After a long pause, open Actions → Sync note and deploy Pages → Enable workflow → Run workflow, or use `gh workflow enable site.yml` then `gh workflow run site.yml`. This implementation does not create dummy commits or add an extra privileged keepalive. See https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows .

Tests: `python3 -m unittest discover -s tests`.

## AI article section

The same daily run separately generates the latest six AI articles from **all RSS entries**, not from the overall latest six. `assets/note-ai.json` retains previously successful AI entries when they leave the feed. URLs are unique within each section; an article can appear in both the chronological note list and the AI topic list.

Title selection uses explicit AI/Claude/Codex/ChatGPT/n8n/AlwaysWhisper terms and Skill operation wording. `assets/ai-curation.json` contains reviewed include/exclude URLs: the October dots usage article is explicitly included after content review, while pair-card and poster-conference articles are excluded. Ambiguous future titles stay out until reviewed and added to this file. The script does not infer topics with a paid model or scrape private articles. Article dates come from RSS publication times, not site sync time. Fetch/validation failure preserves both last successful sections.
