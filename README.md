# py setup ai

CLI that creates and manages uv projects using named package profiles.

## Install

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
uv tool install -e .
```

## Usage

```bash
setup init myproj --profile dl llm --jupyter   # new project (default profile: data)
setup add cv audio                             # add profiles or plain packages
setup rm audio                                 # remove them (keeps packages shared with other profiles)
setup list                                     # show profiles, * = installed
setup start                                    # run JupyterLab on 127.0.0.1:6767
```

Add `-y` to `add`/`rm` to accept prompts. Unknown names get a "did you mean" suggestion or are treated as packages.

## Profiles

`none`, `data`, `dl`, `cv`, `audio`, `scrape`, `llm`, `web`. Contents are defined in `PROFILES` in `setup.py`.

## Installation

With your favorite package manager run.

`uv tool install pysetup-ai`

Or if you want to run it without installing it on your machine use

`uvx pysetup-ai [args]`

## Issues & Contributing

you may suggest profiles, features or fix issues by creating issues and pull requests on this repository.