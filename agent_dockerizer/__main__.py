"""Run with python3 -m agent_dockerizer. Preview output is a JSON file/content map."""
import argparse
import json
from pathlib import Path
import sys

from . import ProjectError, detect, render


def generate(root: Path, outputs: dict[str, str]) -> None:
    """Preflight every destination; use exclusive creation and roll back on I/O failure.

    The project directory must not be concurrently modified during generation.
    """
    for name in outputs:
        current = root
        if current.is_symlink():
            raise ProjectError('Symlinked output paths are unsupported; use a regular project directory.')
        for part in Path(name).parts:
            current = current / part
            if current.is_symlink():
                raise ProjectError('Symlinked output paths are unsupported; remove the symlink first.')
            if current == root / name:
                if current.exists():
                    raise ProjectError('Refusing to overwrite existing output files; move them aside first.')
            elif current.exists() and not current.is_dir():
                raise ProjectError('An output parent is not a directory; move it aside first.')
    created = []
    directories = []
    try:
        for name, content in outputs.items():
            destination = root / name
            missing = []
            parent = destination.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for directory in reversed(missing):
                directory.mkdir()
                directories.append(directory)
            with destination.open('x', encoding='utf-8', newline='\n') as stream:
                created.append(destination)
                stream.write(content)
    except OSError:
        for path in reversed(created):
            path.unlink()
        for path in reversed(directories):
            path.rmdir()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Generate deterministic container artifacts without copying secret values.')
    parser.add_argument('command', choices=('dry-run', 'generate'))
    parser.add_argument('project', type=Path)
    parser.add_argument('--entrypoint', help='Relative Python .py entry point; not needed for npm projects')
    parser.add_argument('--profile', choices=('generic', 'pi', 'opencode'))
    args = parser.parse_args(argv)
    try:
        outputs = render(detect(args.project, entrypoint=args.entrypoint, profile=args.profile))
        if args.command == 'dry-run':
            print(json.dumps(outputs, indent=2, sort_keys=True))
        else:
            generate(args.project, outputs)
            print(json.dumps({'generated': sorted(outputs)}))
    except ProjectError as error:
        print('error: ' + str(error), file=sys.stderr)
        return 2
    except OSError:
        print('error: filesystem operation failed; check directory permissions and available space.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
