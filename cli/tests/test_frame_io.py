"""Regression coverage for frame boundaries, slicing, and temporary-file cleanup."""

from pathlib import Path

import pytest

from cli.frame_io import iter_frames, iter_selected_frames, raw_frame_file, scan_frames


@pytest.mark.parametrize('text, expected', [
    ('', []),
    ('ATOM a\nEND\n', ['ATOM a\n']),
    ('ATOM a\nEND\nEND\nATOM b\n', ['ATOM a\n', 'ATOM b\n']),
    ('HEADER test\nMODEL 1\nATOM a\nENDMDL\nMODEL 2\nATOM b\nATOM c\nENDMDL\nEND\n',
     ['MODEL 1\nATOM a\nENDMDL\n', 'MODEL 2\nATOM b\nATOM c\nENDMDL\n']),
    # Retain the old MODEL-first behavior for incomplete/mixed input too.
    ('MODEL 1\nATOM a\nEND\n', ['MODEL 1\nATOM a\n']),
    ('MODEL 1\nATOM a\nENDMDL\nMODEL 2\nATOM b\n', ['MODEL 1\nATOM a\nENDMDL\n']),
    ('ATOM ignored\nENDMDL\n', ['ENDMDL\n']),
    ('ATOM a\nEND\nREMARK trailing\n', ['ATOM a\n', 'REMARK trailing\n']),
])
def test_frame_text_and_count_preserve_legacy_boundaries(tmp_path, text, expected):
    pdb = tmp_path / 'trajectory.pdb'
    pdb.write_text(text)
    mode, count = scan_frames(pdb)
    assert count == len(expected)
    assert list(iter_frames(pdb, mode)) == expected


@pytest.mark.parametrize('start, stop, step', [(0, 4, 1), (1, 4, 2), (2, 2, 1), (0, 1, 1), (3, 1, 1)])
def test_selected_frames_match_list_slice(tmp_path, start, stop, step):
    frames = [f'ATOM {i}\n' for i in range(4)]
    pdb = tmp_path / 'trajectory.pdb'
    pdb.write_text('END\n'.join(frames) + 'END\n')
    mode, _ = scan_frames(pdb)
    assert list(iter_selected_frames(pdb, mode, start, stop, step)) == frames[start:stop:step]


@pytest.mark.parametrize('fail', [False, True])
def test_temporary_frame_preserves_text_and_is_removed(tmp_path, monkeypatch, fail):
    monkeypatch.setattr('tempfile.tempdir', str(tmp_path))
    try:
        with raw_frame_file('MODEL 1\nATOM a\nENDMDL\n') as filename:
            path = Path(filename)
            assert path.name == '_tmp_raw.pdb'
            assert path.read_text() == 'MODEL 1\nATOM a\nENDMDL\nEND\n'
            if fail:
                raise RuntimeError('simulated processing failure')
    except RuntimeError:
        assert fail
    assert not path.exists()
    assert not path.parent.exists()
