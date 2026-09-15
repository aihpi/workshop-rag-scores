"""Asserts over the pure parts of `scores`. No network, no fixtures.

    uv run pytest -q
    uv run python tests/test_scores.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scores import (
    BUDGET,
    METRIC_COLUMNS,
    METRIC_KEYS,
    by_handle,
    check_submission,
    decode_body,
    pair_tries,
    today_label,
)

TEMPLATE = {
    'handle': 'teal-otter-41',
    'try': '1',
    'config': 'chars_1200__octen',
    'recall_at_5': '0.6341',
    'mrr': '0.7102',
    'ndcg_at_5': '0.6503',
    'evaluations_used': '6',
}
KNOWN = {'chars_1200__octen', 'section_1600__octen'}


# --- the template check ------------------------------------------------------

def test_a_submission_from_the_notebook_is_clean():
    assert check_submission(TEMPLATE, KNOWN) == []


def test_a_missing_field_is_reported_by_name():
    row = {k: v for k, v in TEMPLATE.items() if k != 'mrr'}
    assert check_submission(row, KNOWN) == ['missing mrr']


def test_an_added_field_is_reported():
    problems = check_submission({**TEMPLATE, 'admin': 'true'}, KNOWN)
    assert problems == ['unexpected admin']


def test_a_handle_that_is_not_a_drawn_name_is_reported():
    problems = check_submission({**TEMPLATE, 'handle': 'hanno'}, KNOWN)
    assert len(problems) == 1 and 'adjective-animal-NN' in problems[0]


def test_a_third_round_is_reported():
    problems = check_submission({**TEMPLATE, 'try': '3'}, KNOWN)
    assert problems == ["try '3' is neither 1 nor 2"]


def test_a_metric_outside_zero_to_one_is_reported():
    problems = check_submission({**TEMPLATE, 'recall_at_5': '1.4'}, KNOWN)
    assert problems == ['recall_at_5 1.4 is outside 0 to 1']


def test_a_metric_that_is_not_a_number_is_reported():
    problems = check_submission({**TEMPLATE, 'ndcg_at_5': 'best'}, KNOWN)
    assert problems == ["ndcg_at_5 'best' is not a number"]


def test_more_evaluations_than_the_budget_is_reported():
    problems = check_submission({**TEMPLATE, 'evaluations_used': str(BUDGET + 1)}, KNOWN)
    assert problems == [f'evaluations_used {BUDGET + 1} is outside 1 to {BUDGET}']


def test_a_configuration_that_was_never_measured_is_reported():
    problems = check_submission({**TEMPLATE, 'config': 'chars_7__octen'}, KNOWN)
    assert problems == ["config 'chars_7__octen' was never measured"]


def test_the_configuration_is_not_checked_without_a_grid():
    assert check_submission({**TEMPLATE, 'config': 'anything'}, None) == []


def test_several_problems_are_all_reported():
    problems = check_submission({'handle': 'x', 'try': '9'}, KNOWN)
    assert len(problems) > 2


# --- parsing and pairing -----------------------------------------------------

def test_the_body_survives_prose_around_it():
    body = 'I think section chunking won.\nhandle: lime-crane-07\ntry: 2\nGood workshop!'
    assert decode_body(body) == {'handle': 'lime-crane-07', 'try': '2'}


def test_only_participants_who_came_back_are_paired():
    rows = [
        {'handle': 'a', 'try': '1', 'recall_at_5': '0.4'},
        {'handle': 'a', 'try': '2', 'recall_at_5': '0.8'},
        {'handle': 'b', 'try': '1', 'recall_at_5': '0.5'},          # never came back
        {'try': '1', 'recall_at_5': '0.9'},                         # no handle
    ]
    assert pair_tries(rows) == [{'handle': 'a', 'first': 0.4, 'second': 0.8}]


def test_the_bars_keep_whoever_sent_only_one_round():
    rows = [
        {'handle': 'a', 'try': '1', 'recall_at_5': '0.4'},
        {'handle': 'a', 'try': '2', 'recall_at_5': '0.8'},
        {'handle': 'b', 'try': '1', 'recall_at_5': '0.5'},          # never came back
        {'handle': 'c', 'try': '2', 'recall_at_5': '0.7'},          # missed the first round
    ]
    assert by_handle(rows) == {'a': {'1': {'recall_at_5': 0.4}, '2': {'recall_at_5': 0.8}},
                               'b': {'1': {'recall_at_5': 0.5}}, 'c': {'2': {'recall_at_5': 0.7}}}
    assert [row['handle'] for row in pair_tries(rows)] == ['a']


def test_every_metric_of_a_round_reaches_the_figures():
    rows = [
        {'handle': 'a', 'try': '1', 'recall_at_5': '0.4', 'mrr': '0.3', 'ndcg_at_5': '0.2'},
        {'handle': 'b', 'try': '1', 'recall_at_5': '0.5', 'mrr': 'not a number'},
    ]
    assert by_handle(rows)['a']['1'] == {'recall_at_5': 0.4, 'mrr': 0.3, 'ndcg_at_5': 0.2}
    # An unreadable MRR costs that one panel a bar, not the whole submission.
    assert by_handle(rows)['b']['1'] == {'recall_at_5': 0.5}


def test_the_figures_can_label_every_metric():
    assert tuple(METRIC_COLUMNS) == METRIC_KEYS


def test_a_repeated_round_keeps_the_last_submission():
    rows = [
        {'handle': 'a', 'try': '1', 'recall_at_5': '0.4'},
        {'handle': 'a', 'try': '1', 'recall_at_5': '0.6'},          # submitted the same round twice
        {'handle': 'a', 'try': '2', 'recall_at_5': '0.8'},
    ]
    assert pair_tries(rows) == [{'handle': 'a', 'first': 0.6, 'second': 0.8}]


def test_todays_label_is_a_session_label():
    label = today_label()
    assert label.startswith('session-') and len(label) == len('session-2026-09-14')


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for test in tests:
        test()
    print(f'{len(tests)} tests passed')


def test_the_notebook_defines_its_controls_before_it_can_stop():
    """A cell that stops before defining what its dependents read leaves them with a NameError as
    soon as marimo runs them without re-running that cell, which is what reloading a changed file
    into a live notebook does. Controls exist whatever happens; only their rendering is conditional.
    """
    import ast

    path = Path(__file__).resolve().parents[1] / 'instructor.py'
    late = []
    for cell in [n for n in ast.walk(ast.parse(path.read_text(encoding='utf-8')))
                 if isinstance(n, ast.FunctionDef) and n.name == '_']:
        if not isinstance(cell.body[-1], ast.Return) or cell.body[-1].value is None:
            continue
        exported = {n.id for n in ast.walk(cell.body[-1]) if isinstance(n, ast.Name)}
        if not any(name.startswith('ui_') for name in exported):
            continue
        stops = [i for i, node in enumerate(cell.body)
                 if any(isinstance(s, ast.Attribute) and s.attr == 'stop'
                        and isinstance(s.value, ast.Name) and s.value.id == 'mo'
                        for s in ast.walk(node))]
        if not stops:
            continue
        defined_late = {n.id for node in cell.body[stops[0] + 1:] for n in ast.walk(node)
                        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        late += [f'line {cell.lineno} defines {name} after a stop'
                 for name in sorted(defined_late & exported)]
    assert late == []
