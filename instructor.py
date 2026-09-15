# ruff: noqa: PLR1711, B018  marimo cells end with an explicit return and render a bare expression

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium", app_title="Workshop scores")


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        """
        # Workshop scores

        The instructor view over the submissions this repository collects. Load them, check what
        arrived, label the session, then show the room how it did.

        Reading needs nothing. **Labelling needs `gh` logged in** as someone with triage rights here,
        so run `gh auth login` first if the buttons report a failure.
        """
    )
    return


@app.cell
def _():
    import marimo as mo  # the reactive notebook itself
    import matplotlib.pyplot as plt  # the before-and-after plot
    import numpy as np  # medians

    import scores  # reading, checking and labelling the submissions
    return mo, np, plt, scores


@app.cell(hide_code=True)
def _(mo):
    ui_load = mo.ui.run_button(label='Load submissions')
    ui_load
    return (ui_load,)


@app.cell(hide_code=True)
def _(mo, scores, ui_load):
    # Everything below reads these five names, so they are defined before anything can go wrong
    # and stay empty until the button is pressed. A cell that stops before its definitions leaves
    # its dependents with a NameError whenever marimo runs them without re-running this cell.
    golds, known_configs, submissions, pulls = {}, None, [], []

    if ui_load.value:
        try:
            with mo.status.spinner(title='Reading the measured grid...'):
                golds, known_configs = scores.best_known()
        except OSError:
            # The grid only supplies the reference lines and the list of measured configurations.
            # Without it the submissions still read fine, so say so and carry on.
            golds, known_configs = {}, None

        try:
            with mo.status.spinner(title='Reading the submissions...'):
                submissions = scores.fetch_scores()
                pulls = scores.open_pulls()
        except OSError as exc:
            submissions, pulls = [], []
            mo.output.append(mo.callout(mo.md(f'GitHub is not reachable: `{exc}`'), kind='danger'))
    else:
        mo.output.append(mo.md('*Press Load submissions.*'))

    checked = [{**row, 'problems': scores.check_submission(row['body'], known_configs)}
               for row in submissions]
    return checked, golds, known_configs, pulls, submissions


@app.cell(hide_code=True)
def _(checked, golds, known_configs, mo, pulls, ui_load):
    mo.stop(not ui_load.value, mo.md(''))
    mo.stop(not checked and not pulls, mo.md('*No submissions yet.*'))

    _flagged = [row for row in checked if row['problems']]
    _notes = []
    if pulls:
        _notes.append(mo.md(
            '**Open pull requests on this repository.** A score arrives as an issue and never as a '
            'pull request, so these are something else and want a look:\n\n'
            + '\n'.join(f'- #{p["number"]} *{p["title"]}* by `{p["author"]}`' for p in pulls)))
    if _flagged:
        _notes.append(mo.md(
            '**Submissions that do not match the template.** They stay out of the session below:\n\n'
            + '\n'.join(f'- #{row["number"]} by `{row["author"]}`: ' + '; '.join(row['problems'])
                        for row in _flagged)))
    if known_configs is None:
        _notes.append(mo.md(
            'The measured grid could not be fetched, so configurations are not checked and the '
            '`best known` lines are missing from the figures.'))

    mo.callout(mo.vstack(_notes), kind='warn') if _notes else mo.md(
        f'*Everything matches the template. Best known Recall@5 is '
        f'{golds["recall_at_5"]:.1%}.*' if golds else '*Everything matches the template.*')
    return


@app.cell(hide_code=True)
def _(checked, mo):
    mo.stop(not checked)

    # Values come from issue bodies anyone can write, so they are shown as plain table cells and
    # never rendered as markdown.
    _rows = [{
        'issue': row['number'],
        'opened': row['created_at'],
        'handle': row['body'].get('handle', ''),
        'try': row['body'].get('try', ''),
        'config': row['body'].get('config', ''),
        'Recall@5': row['body'].get('recall_at_5', ''),
        'session': ', '.join(row['sessions']) or '—',
        'status': 'ok' if not row['problems'] else '; '.join(row['problems']),
    } for row in checked]
    mo.ui.table(_rows, selection=None, pagination=True)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""## Confirm a session""")
    return


@app.cell(hide_code=True)
def _(mo):
    # What has been done already, which is what greys the two buttons out and what the notes
    # underneath are drawn from. Only the two worker cells write it.
    get_done, set_done = mo.state({'label': None, 'applied': set(), 'notes': [], 'kind': 'neutral'})
    return get_done, set_done


@app.cell(hide_code=True)
def _(checked, mo, scores):
    ui_label = mo.ui.text(value=scores.today_label(), label='session label', full_width=False)
    ui_label if checked else mo.md('')
    return (ui_label,)


@app.cell(hide_code=True)
def _(checked, mo):
    # Only clean, unlabelled submissions can be picked, so an off-template issue cannot be
    # confirmed into a session by a stray click.
    _open = {f'#{row["number"]}  {row["body"].get("handle", "?")}  try {row["body"].get("try", "?")}'
             f'  {row["body"].get("recall_at_5", "?")}': row['number']
             for row in checked if not row['problems'] and not row['sessions']}

    ui_pick = mo.ui.multiselect(_open, label='submissions to confirm')
    (mo.vstack([ui_pick, mo.md(f'*{len(_open)} submissions are clean and not yet in a session.*')])
     if checked else mo.md(''))
    return (ui_pick,)


@app.cell(hide_code=True)
def _(checked, get_done, mo, ui_label, ui_pick):
    # A button goes grey once its own action has been done, which is as early as marimo can grey
    # it: no cell can re-render while another cell is still working. The spinner in the worker
    # cell is what says the notebook is busy in the meantime.
    _done = get_done()
    _made = _done['label'] == ui_label.value
    _applied = bool(ui_pick.value) and set(ui_pick.value) <= _done['applied']

    ui_create = mo.ui.run_button(label='Label created' if _made else 'Create label', disabled=_made)
    ui_apply = mo.ui.run_button(label='Applied' if _applied else 'Apply to selected',
                                disabled=_applied)
    mo.hstack([ui_create, ui_apply], justify='start') if checked else mo.md('')
    return ui_apply, ui_create


@app.cell(hide_code=True)
def _(mo, scores, set_done, ui_create, ui_label):
    mo.stop(not ui_create.value)
    try:
        with mo.status.spinner(title='Creating the label...'):
            _said = scores.ensure_label(ui_label.value)
    except scores.NotAuthenticated as exc:
        _refused = str(exc)
        set_done(lambda done: {**done, 'notes': [_refused], 'kind': 'danger'})
    else:
        set_done(lambda done: {**done, 'label': ui_label.value, 'kind': 'neutral',
                               'notes': [f'{_said}. Press Load submissions again to refresh.']})
    mo.md('')
    return


@app.cell(hide_code=True)
def _(mo, scores, set_done, ui_apply, ui_label, ui_pick):
    mo.stop(not ui_apply.value)
    mo.stop(not ui_pick.value, mo.md('*Pick at least one submission.*'))

    # One `gh issue edit` per issue, one after another, so the bar is the honest way to show it.
    _numbers = list(ui_pick.value)
    _lines = []
    try:
        for _number in mo.status.progress_bar(_numbers, title='Labelling', remove_on_exit=True):
            _lines += scores.apply_label([_number], ui_label.value)
    except scores.NotAuthenticated as exc:
        _refused = str(exc)
        set_done(lambda done: {**done, 'notes': [*_lines, _refused], 'kind': 'danger'})
    else:
        set_done(lambda done: {**done, 'applied': done['applied'] | set(_numbers),
                               'notes': _lines, 'kind': 'neutral'})
    mo.md('')
    return


@app.cell(hide_code=True)
def _(get_done, mo):
    # Rendered from the state rather than from the cells that did the work, because those cells
    # re-run and stop the moment their button is rebuilt.
    _done = get_done()
    _notes = mo.md('\n'.join(f'- {line}' for line in _done['notes']))
    (mo.callout(_notes, kind='danger') if _done['kind'] == 'danger' else _notes) if _done['notes'] \
        else mo.md('')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""## How the room did""")
    return


@app.cell(hide_code=True)
def _(mo):
    ui_refresh = mo.ui.run_button(label='Load sessions')
    ui_refresh
    return (ui_refresh,)


@app.cell(hide_code=True)
def _(mo, scores, ui_refresh):
    _labels = []
    if ui_refresh.value:
        try:
            with mo.status.spinner(title='Reading the sessions...'):
                _labels = scores.session_labels()
        except OSError as exc:
            mo.output.append(mo.callout(mo.md(f'GitHub is not reachable: `{exc}`'), kind='warn'))

    ui_session = mo.ui.dropdown({lab: lab for lab in _labels},
                                value=_labels[0] if _labels else None, label='session')
    ui_session if ui_refresh.value else mo.md('*Press Load sessions.*')
    return (ui_session,)


@app.cell(hide_code=True)
def _(mo, scores, ui_session):
    # Both names are defined whatever happens, and the plotting cells below stop on an empty
    # session themselves. A cell that stops before defining what its dependents read leaves them
    # with a NameError the moment marimo runs them without re-running this one, which is what a
    # notebook reloaded from a changed file on disk does.
    tries = {}
    if ui_session.value is not None:
        # Fetched here and not in the plotting cells, so switching the view costs nothing.
        with mo.status.spinner(title='Reading the session...'):
            tries = scores.by_handle(scores.fetch_session(ui_session.value))

    ui_view = mo.ui.radio({'first try': '1', 'second try': '2', 'both': 'both'},
                          value='both', inline=True, label='show')

    if ui_session.value is None:
        mo.md('*No confirmed session yet.*')
    elif not tries:
        mo.md('*Nothing confirmed into this session yet.*')
    else:
        ui_view
    return tries, ui_view


@app.cell(hide_code=True)
def _(golds, mo, np, plt, scores, tries, ui_view):
    mo.stop(not tries, mo.md(''))
    _which = ui_view.value

    # The handles are ordered once, on the Recall@5 of the round on show, and that order is reused
    # in all three panels, so a participant finds their own bar in the same place across the row.
    def _rank(handle):
        rounds = tries[handle]
        if _which != 'both':
            return (0, -rounds[_which]['recall_at_5'])
        first = rounds.get('1', {}).get('recall_at_5')
        if first is not None:
            return (0, -first)
        # Whoever has no first try cannot be placed against one, so they go to the end.
        return (1, -rounds.get('2', {}).get('recall_at_5', 0.0))

    if _which == 'both':
        _handles = sorted(tries, key=_rank)
    else:
        _handles = sorted((h for h in tries if _which in tries[h]), key=_rank)
    mo.stop(not _handles, mo.md('*Nobody sent that round in yet.*'))

    _fig, _axes = plt.subplots(1, 3, figsize=(13.5, 4.2))
    _x = np.arange(len(_handles))
    for _ax, (_key, _label) in zip(_axes, scores.METRIC_COLUMNS.items()):
        def _values(attempt, key=_key):
            return [tries[h].get(attempt, {}).get(key, 0.0) for h in _handles]

        if _which == 'both':
            _ax.bar(_x - 0.19, _values('1'), 0.38, color='#9a9a9a', label='first try')
            _ax.bar(_x + 0.19, _values('2'), 0.38, color='#b51f1f', label='second try')
        else:
            _ax.bar(_x, _values(_which), 0.6,
                    color='#9a9a9a' if _which == '1' else '#b51f1f',
                    label='first try' if _which == '1' else 'second try')

        # The best known value is written outside the axes, because three panels carry three
        # different maxima and one shared legend cannot say them all.
        if _key in golds:
            _ax.axhline(golds[_key], linestyle='--', color='#1a1a1a', linewidth=1)
            _ax.annotate(f'{golds[_key]:.0%}', xy=(1.02, golds[_key]),
                         xycoords=('axes fraction', 'data'), va='center', fontsize=8,
                         color='#1a1a1a', annotation_clip=False)

        _ax.set_title(_label, fontsize=10)
        _ax.set_xticks(_x, _handles, rotation=45, ha='right', fontsize=7)
        _ax.set_ylim(bottom=0)
        for _side in ('top', 'right'):
            _ax.spines[_side].set_visible(False)
    _axes[0].set_ylabel('score')

    _handles_, _labels_ = _axes[0].get_legend_handles_labels()
    _fig.legend(_handles_, _labels_, frameon=False, ncols=2, loc='upper left',
                bbox_to_anchor=(0.01, 1.0), fontsize=9)
    _fig.tight_layout(rect=(0, 0, 1, 0.93))
    _fig
    return


@app.cell(hide_code=True)
def _(golds, mo, np, plt, scores, tries):
    mo.stop(not tries, mo.md(''))

    _fig, _axes = plt.subplots(1, 3, figsize=(13.5, 4.2))
    _jitter = np.random.default_rng(0)
    _counts = {}
    for _ax, (_key, _label) in zip(_axes, scores.METRIC_COLUMNS.items()):
        _rounds = [[row[attempt][_key] for row in tries.values()
                    if attempt in row and _key in row[attempt]] for attempt in ('1', '2')]
        _counts[_key] = _rounds
        _ax.boxplot(_rounds, tick_labels=['first try', 'second try'],
                    medianprops={'color': '#b51f1f', 'linewidth': 2},
                    boxprops={'color': '#6a6a6a'}, whiskerprops={'color': '#6a6a6a'},
                    capprops={'color': '#6a6a6a'}, flierprops={'markeredgecolor': '#9a9a9a'})

        # A workshop room is a dozen people at most, so the points themselves carry more than
        # the box.
        for _at, _values in enumerate(_rounds, start=1):
            _ax.scatter(_at + _jitter.uniform(-0.07, 0.07, len(_values)), _values,
                        s=18, color='#9a9a9a', alpha=0.6, zorder=3)

        if _key in golds:
            _ax.axhline(golds[_key], linestyle='--', color='#1a1a1a', linewidth=1)
            _ax.annotate(f'{golds[_key]:.0%}', xy=(1.02, golds[_key]),
                         xycoords=('axes fraction', 'data'), va='center', fontsize=8,
                         color='#1a1a1a', annotation_clip=False)

        _ax.set_title(_label, fontsize=10)
        _ax.set_ylim(bottom=0)
        for _side in ('top', 'right'):
            _ax.spines[_side].set_visible(False)
    _axes[0].set_ylabel('score')
    _fig.tight_layout()

    def _median(values):
        return f'{float(np.median(values)):.1%}' if values else 'nothing'

    _first, _second = _counts['recall_at_5']
    mo.vstack([
        _fig,
        mo.md(f'*Recall@5: {len(_first)} first tries, median {_median(_first)}; {len(_second)} '
              f'second tries, median {_median(_second)}. The dashed line in each panel is the best '
              'measured configuration for that metric.*'),
    ])
    return


if __name__ == "__main__":
    app.run()
