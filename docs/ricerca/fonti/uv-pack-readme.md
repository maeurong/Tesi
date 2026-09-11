## uv-pack

[![Check Status](https://github.com/davnn/uv-pack/actions/workflows/check.yml/badge.svg)](https://github.com/davnn/uv-pack/actions?query=workflow%3Acheck) [![Semantic Versions](https://camo.githubusercontent.com/5ee5f3f88b97e3908db84dd430ce32386e72f1ac3ae8d5abdbe27e672a9bd27e/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f2532302532302546302539462539332541362546302539462539412538302d73656d616e7469632d2d76657273696f6e732d6531303037392e737667)](https://github.com/davnn/uv-pack/releases)

Bundle a locked `uv` environment into a self-contained, offline-installable directory. The output includes pinned requirements, third-party wheels, locally built wheels, and a portable Python interpreter.

## What it does

- Exports locked requirements from your `uv` lock file.
- Downloads third-party wheels into `pack/wheels/`.
- Builds local workspace packages into `pack/vendor/`.
- Downloads a python-build-standalone archive into `pack/python/` (unless you skip the `python` step).
- Writes `unpack.sh` and `unpack.ps1` to unpack the resulting venv offline.

## Install

Install `uv-pack` as a dev-dependency.

```
uv add --dev uv-pack
```

Once installed, run using:

```
uv run uv-pack --help
```

You can also use `uv-pack` as a tool.

```
# specify the python version!
uv tool run --python 3.12 uv-pack --help
# or using uvx (equivalent)
uvx --python 3.12 uv-pack --help
```

## CLI

```
uv-pack [STEPS...]
```

Options:

- `STEPS`: subset of pipeline steps (default: `clean export download build python`)
- `-s, --skip`: skip a pipeline step (can be supplied multiple times)
- `-o, --output-directory`: path to output directory (default: `./pack`)
- `-v, --verbose`: show more detailed pack progress logging
- `--uv-build`: extra args passed to `uv build`
- `--uv-export`: extra args passed to `uv export`
- `--pip-download`: extra args passed to `pip download`

Pipeline steps:

- `clean`: remove the output directory
- `export`: write `requirements.txt` files for third-party and local packages
- `download`: download third-party wheels and sources
- `build`: build local wheels and compile the combined requirements file
- `python`: download a python-build-standalone archive for the current Python version, platform, and ABI flavor

## Example

```
# run the entire pipeline (default) with verbose outputs
uv-pack --verbose
# only clean and export the requirements
uv-pack clean export
```

## Output layout

```
pack/
  requirements.txt
  wheels/
    requirements.txt
  vendor/
    requirements.txt
  python/   # (omitted when the python step is skipped)
  unpack.sh
  unpack.ps1
  .gitignore
  README.md
```

## Unpack and install offline

POSIX (sh/bash/zsh):

```
./pack/unpack.sh
```

PowerShell:

```
.\pack\unpack.ps1
```

All scripts also accept `VENV_DIR`, `PYTHON_DIR` and `BASE_PY` environment variables. Use `BASE_PY` when you skipped the `python` step during packing to provide a system python interpreter. `VENV_DIR` (default = `.venv`) and `PYTHON_DIR` (default = `.python`) can be used to customize the target python and venv directory. Set `VENV_DIR=""` to skip creating a virtual environment and install directly into `BASE_PY`.

## Configuration

`UV_PYTHON_INSTALL_MIRROR` can override the GitHub API endpoint to retrieve the Python releases, default is: [https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest](https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest).

`GITHUB_TOKEN` can be used to authenticate requests to the GitHub API to prevent possible rate-limiting.

## Limitations

- The pack process must happen in the `pyproject.toml` or `uv.toml` directory, typically the repository root, because `uv` exports relative paths to the project root.
- The build platform is expected to equal the usage platform; it is currently not possible to pack an environment for a different platform.
- The embedded Python ABI flavor is inferred from the interpreter running `uv-pack`. Run `uv-pack` with free-threaded Python to produce a free-threaded pack.
- The project Python version is ignored when running `uv-pack` as a tool (`uv tool run` or `uvx`) and should be specified using `uv tool run --python 3.11 uv-pack` or `uvx --python 3.11 uv-pack`, see [uv#uv5951](https://github.com/astral-sh/uv/issues/5951) and [uv#8206](https://github.com/astral-sh/uv/issues/8206).
- The download process can be slow because `pip download` is used as there is no native (parallel) uv download option available for wheels, see [uv#3163](https://github.com/astral-sh/uv/issues/3163).

## FAQ

#### How do I pass extra options to uv export or another command?

Use `--uv-export` to forward arguments, for example:

- `uv-pack --uv-export "--package $MY_PACKAGE"` to export only a specific workspace package
- `uv-pack --uv-export "--locked  --dev"` to include dev-deps and ensure an up-to-date lock file
- `uv-pack --uv-export "--all-extras"` to include all extra dependencies

The same is true for `--uv-build` and `--pip-download` arguments.

#### How do I specify index-urls and extra-index-urls?

The index urls set in `pyproject.toml` and `uv.toml` are not configured by default for the wheel download (`pip download`), you can specify them as:

- `uv-pack --pip-download "--index-url $MY_INDEX --extra-index-url $MY_EXTRA_INDEX"`

#### How do I skip bundling Python?

Skip the `python` step: `uv-pack --skip python`. When unpacking, set `BASE_PY` to a system Python path.

#### How do I install directly into a system Python instead of creating.venv?

Set `BASE_PY` to the target interpreter and `VENV_DIR=""` when unpacking. For example:

```
BASE_PY=/usr/bin/python3 VENV_DIR="" sh ./pack/unpack.sh
```

#### How do I rerun without deleting the existing pack directory?

Skip the `clean` step: `uv-pack --skip clean`. Note that this automatically re-uses downloaded wheels and the downloaded Python interpreter.

#### How do I only re-build my package if my pack is already complete?

Run only `uv-pack build`.

#### How can I use my pack?

Move the pack to the final location and, depending on the shell used, call `unpack.sh` or `unpack.ps1`. Don't move the virtual environment or pack folder after unpacking (hardcoded paths).