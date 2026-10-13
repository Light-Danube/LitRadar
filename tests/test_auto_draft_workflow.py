"""Exercise the workflow shell with a local fake gh; no GitHub mutations."""
import os
from pathlib import Path
import shutil
import subprocess
import textwrap

import pytest


@pytest.mark.skipif(shutil.which('bash') is None, reason='Workflow shell requires bash')
@pytest.mark.parametrize('count,list_exit,creates', [('0', 0, True), ('1', 0, False), ('0', 1, False)])
def test_draft_workflow_creates_only_when_listing_succeeds_and_no_pr_exists(tmp_path, count, list_exit, creates):
    workflow = Path(__file__).resolve().parents[1] / '.github/workflows/auto-draft-pr.yml'
    script = textwrap.dedent(workflow.read_text().split('        run: |\n', 1)[1])
    gh = tmp_path / 'gh'
    gh.write_text('''#!/bin/bash
printf '%s\\n' "$@" >> "$CALL_LOG"
if [ "$1 $2" = "pr list" ]; then
  echo "$TEST_COUNT"
  exit "$TEST_LIST_EXIT"
fi
if [ "$1 $2" = "pr create" ]; then
  exit 0
fi
exit 99
''')
    gh.chmod(0o700)
    log = tmp_path / 'calls'
    # Metacharacters must stay data in the title and arguments.
    head = 'codex/test-$(touch SHOULD_NOT_EXIST)'
    result = subprocess.run(['bash', '-c', script], cwd=tmp_path, capture_output=True, text=True,
                            env={'PATH': str(tmp_path) + os.pathsep + os.defpath,
                                 'CALL_LOG': str(log), 'TEST_COUNT': count,
                                 'TEST_LIST_EXIT': str(list_exit), 'PR_HEAD': head,
                                 'PR_BASE': 'main', 'GH_REPO': 'fixture/repository'})
    args = log.read_text().splitlines()
    assert (result.returncode == 0) == (list_exit == 0)
    assert ('create' in args) == creates
    assert not (tmp_path / 'SHOULD_NOT_EXIST').exists()
    if creates:
        assert '--draft' in args
        assert args[args.index('--title') + 1] == f'Codex update: {head}'
        create_args = args[args.index('create') + 1:]
        assert create_args[create_args.index('--head') + 1] == head
        assert create_args[create_args.index('--base') + 1] == 'main'
