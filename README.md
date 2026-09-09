<div align="center">
  <img src="00_aisc/img/logo_aisc_bmftr.jpg" alt="HPI AI Service Centre, funded by the BMFTR" width="420">
</div>

# workshop-rag-scores

Anonymous score submissions for the chunking exercise of the HPI AI Service Centre's **RAG II** workshop. This repository holds no code. Its issue tracker is the collection box.

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

Before the session, create the label for it:

```bash
gh api -X POST repos/aihpi/workshop-rag-scores/labels -f name=session-2026-09-15 -f color=0E8A16 -f description="RAG II, 15 September 2026"
```

After each round, confirm the submissions that belong to the session:

```bash
gh issue list --repo aihpi/workshop-rag-scores --label score --state all --limit 100
gh issue edit <number> --repo aihpi/workshop-rag-scores --add-label session-2026-09-15
```

The results view at the bottom of the playground notebook reads only labelled issues, so a score submitted after the workshop cannot change a past session. When the session is over, close the issues; they stay readable as a record.

## Licence

[MIT](LICENSE), like the workshop material itself.
