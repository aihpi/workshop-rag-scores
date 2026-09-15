<div align="center">
  <img src="00_aisc/img/logo_aisc_bmftr.jpg" alt="HPI AI Service Centre, funded by the BMFTR" width="420">
</div>

# workshop-rag-scores

Anonymous score submissions for the chunking exercise of the HPI AI Service Centre's **RAG II** workshop. Its issue tracker is the collection box, and `instructor.py` is the view over it.

## What this is for

The workshop opens and closes with the same five-minute exercise: participants tune a chunking and embedding configuration in the [`w2_00_chunking_playground`](https://github.com/aihpi/workshop-rag) notebook, once before they have been taught anything and once after. Comparing the two rounds in front of the room is the point of the exercise, so the scores have to be collected somewhere both the notebook and the instructor can reach.

An issue is the cheapest thing that works. Anyone with a GitHub account can open one on a public repository, no write access has to be granted before the workshop or revoked afterwards, and two submissions can never conflict with each other.

## What a submission contains

One issue per attempt, opened by the notebook with everything already filled in:

```
handle: teal-otter-41
try: 1
config: chars_1200__octen
recall_at_5: 0.6341
mrr: 0.7102
ndcg_at_5: 0.6503
evaluations_used: 6
```

The handle is a random name the notebook draws once and keeps in a gitignored file on the participant's own machine. It exists so that a participant's first and second attempt can be paired, and it is the only identifier in the data. No names, no e-mail addresses, no answers, nothing about the person.

Anonymity has one limit worth stating plainly: GitHub records who opened an issue, so the account is visible on the issue itself. The plot the room sees never shows accounts, only the distribution of scores.

## For the instructor

Everything happens in one notebook. Clone this repository and run it:

```bash
uv sync
```

```bash
uv run marimo run instructor.py
```

It loads every submission, shows what arrived, creates the `session-YYYY-MM-DD` label and applies it to the attempts that belong to the session.

Two figures then show the room how it did. The first is a bar of Recall@5 per handle, switchable between the first try, the second try and both side by side; the second is a box plot of the two rounds with every submission drawn over it. Both carry the best measured configuration as a dashed line, which is the ceiling nobody in the room is expected to reach.

Every slow button shows a spinner while it works, and labelling shows a bar because it edits one issue at a time. A button that has done its work goes grey; marimo runs one cell at a time, so that happens once the work is finished rather than while it runs.

Reading needs no credentials. **Labelling needs `gh` logged in** as someone with triage rights here, so run `gh auth login` once. Someone else who clones this repository can read the submissions, as anyone can on a public repository, but their label calls are refused.

Only labelled submissions count, so a score sent in after the workshop cannot change a past session. Submissions that do not match the template the notebook writes are flagged with a reason and cannot be added to a session by mistake. When the session is over, close the issues; they stay readable as a record.

A pull request is never a submission. If one appears, the notebook says so at the top, because that is someone proposing a change to this repository rather than a score.

## Licence

[MIT](LICENSE), like the workshop material itself.
