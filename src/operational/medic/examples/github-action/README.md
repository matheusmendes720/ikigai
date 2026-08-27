# medic-action — GitHub Action wrapper

Run `medic` against a PR and post the report as a review comment.

## Inputs

| name | required | default | meaning |
|---|---|---|---|
| `target` | yes | `.` | Path inside the checkout to inspect |
| `repo`   | no  | (workflow repo) | GitHub repo for review/issue posting |
| `token`  | yes | `${{ github.token }}` | Token with PR write + checks write |
| `workflow` | no | `examples/workflow/pr-review.yaml` | Workflow YAML |
| `post`   | no | `false` | Post the review back |
| `fail_on`| no | `0` | Minimum health score; below this, action fails |

## Sample workflow

```yaml
on: [pull_request]
jobs:
  medic:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      checks: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: ./examples/github-action
        with:
          target: ./packages/core
          post:   true
          fail_on: 60
```
