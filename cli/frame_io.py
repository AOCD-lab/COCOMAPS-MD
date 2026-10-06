"""Bounded-memory PDB frame I/O; molecular selections stay in the runner."""

from contextlib import closing, contextmanager
from itertools import islice
from pathlib import Path
import tempfile


def scan_frames(pdb_file):
    """Count frames using the runner's existing MODEL-first, END fallback rules.

    A counting pass lets the caller retain exact progress totals and slicing
    without keeping the full trajectory in memory. Even incomplete MODEL files
    retain the legacy fallback behavior.
    """
    model_frames = end_frames = 0
    has_content = False
    with open(pdb_file) as source:
        for line in source:
            record = line[:6].strip()
            if record == 'ENDMDL':
                model_frames += 1
            if record == 'END':
                end_frames += int(has_content)
                has_content = False
            else:
                has_content = True
    if model_frames:
        return 'model', model_frames
    return 'end', end_frames + int(has_content)


def iter_frames(pdb_file, mode):
    """Yield the exact text formerly collected in raw_frames, one frame at a time."""
    with open(pdb_file) as source:
        lines = []
        in_model = False
        for line in source:
            record = line[:6].strip()
            if mode == 'model':
                if record == 'MODEL':
                    in_model = True
                    lines = [line]
                elif record == 'ENDMDL':
                    lines.append(line)
                    yield ''.join(lines)
                    lines = []
                    in_model = False
                elif in_model:
                    lines.append(line)
            elif record == 'END':
                if lines:
                    yield ''.join(lines)
                    lines = []
            else:
                lines.append(line)
        if mode == 'end' and lines:
            yield ''.join(lines)


@contextmanager
def raw_frame_file(raw_text):
    """Use OS temporary storage, closing/removing files on success or failure.

    In Docker this defaults to container-local /tmp rather than the output bind
    mount. Keep the basename and text identical to the previous implementation.
    """
    with tempfile.TemporaryDirectory(prefix='cocomaps-frame-') as directory:
        path = Path(directory) / '_tmp_raw.pdb'
        with path.open('w') as target:
            target.write(raw_text)
            if not raw_text.rstrip().endswith('END'):
                target.write('END\n')
        yield str(path)


def iter_selected_frames(pdb_file, mode, start, stop, step):
    """Close the source even when the requested range ends before EOF."""
    with closing(iter_frames(pdb_file, mode)) as frames:
        yield from islice(frames, start, stop, step)
