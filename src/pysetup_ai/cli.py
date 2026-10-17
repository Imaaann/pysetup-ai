#!/usr/bin/env python3
import argparse
import difflib
import json
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

STATE_FILE = ".pysetup_profiles.json"

JUPYTER_BASE = ["jupyterlab", "ipykernel", "jupyterlab-lsp", "python-lsp-server"]
JUPYTER_PORT = 6767
JUPYTER_TOKEN = "SETUP_AI_JUPYTER_TOKEN"

PROFILES: dict[str, list[str]] = {
    "none": [],
    "data": ["numpy", "pandas", "matplotlib", "seaborn", "scikit-learn", "lightgbm"],
    "dl": [
        "torch",
        "torchvision",
        "torchaudio",
        "transformers",
        "datasets",
        "accelerate",
    ],
    "cv": ["opencv-python-headless", "pillow", "timm"],
    "audio": ["librosa", "soundfile", "faster-whisper"],
    "scrape": ["httpx", "beautifulsoup4", "lxml", "playwright"],
    "llm": ["transformers", "huggingface-hub", "sentence-transformers", "smolagents"],
    "web": ["fastapi", "uvicorn", "sqlmodel", "pydantic-settings", "httpx", "asyncpg"],
}

def uv(*args, cwd=None):
    if shutil.which("uv") is None:
        sys.exit("Error: 'uv' not found on PATH. Install it from https://docs.astral.sh/uv/")

    print(f"args -> {args}")
    print(f"$ uv {' '.join(args)}")
    try:
        subprocess.run(["uv", *args], cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error: 'uv {args[0]}' failed with exit code {e.returncode}.")

def find_project_root():
    for p in [Path.cwd(), *Path.cwd().parents]:
        if (p / "pyproject.toml").exists():
            return p
    sys.exit("Error: not inside a uv project (no pyproject.toml found).")

def load_state_file(root):
    f = root / STATE_FILE
    return json.loads(f.read_text()) if f.exists() else {"profiles": []}

def save_state_file(root, state):
    f = root / STATE_FILE
    f.write_text(json.dumps(state, indent=2))

def ask(prompt, options, assume_yes=False):
    if assume_yes or not sys.stdin.isatty():
        return options[0]
    answer = input(f"{prompt} [{'/'.join(options)}]: ").strip().lower()
    return answer if answer in options else "cancel"

def resolve(target, assume_yes):
    if target in PROFILES:
        return ("profile", target)

    keys = list(PROFILES.keys())
    print(keys)
    close = difflib.get_close_matches(target, keys, n=1, cutoff=0.5)
    print(close)
    if close:
        choice = ask(
            f"'{target}' isn't a profile. Did you mean profile '{close[0]}'?",
            ["profile", "package", "cancel"],
            assume_yes,
        )
        if choice == "profile":
            return ("profile", close[0])
        if choice == "package":
            return ("package", target)
        return None

    choice = ask(
        f"'({target})' Isn't a profile. Do you want to treat it as a package?",
        ["yes", "cancel"],
    )
    return ("package", target) if choice == "yes" else None

# COMMAND START HERE

def cmd_init(args):
    if Path(args.project_name).exists():
        sys.exit(f"Error: '{args.project_name}' already exists.")

    uv("init", args.project_name)



    root = Path(args.project_name)
    root.mkdir(exist_ok=True)
    
    if args.jupyter:
        uv("add", "--dev", *JUPYTER_BASE, cwd=root)

    packages = sorted({p for name in args.profile for p in PROFILES[name]})
    if packages:
        uv("add", *packages, cwd=root)

    save_state_file(root, {"profiles": sorted(args.profile)})

def cmd_add(args):
    root = find_project_root()
    state = load_state_file(root)

    for target in args.targets:
        resolved = resolve(target, args.yes)
        if resolved is None:
            continue
        kind, name = resolved
        if kind == "profile":
            uv("add", *PROFILES[name], cwd=root)
            if name not in state["profiles"]:
                state["profiles"].append(name)
        else:
            uv("add", name, cwd=root)

    save_state_file(root, state)

def cmd_rm(args):
    root = find_project_root()
    state = load_state_file(root)

    for target in args.targets:
        resolved = resolve(target, args.yes)
        if resolved is None:
            continue
        kind, name = resolved
        if kind == "profile":
            still_installed = [p for p in state["profiles"] if p != name]
            protected = {pkg for p in still_installed for pkg in PROFILES[p]} | set(JUPYTER_BASE)
            to_remove = [pkg for pkg in PROFILES[name] if pkg not in protected]

            if to_remove:
                uv("remove", *to_remove, cwd=root)
                
            state["profiles"] =  still_installed
        else:
            if name in JUPYTER_BASE:
                print(f"Refusing to remove a jupyter package `{name}`.")
                continue

            installed = {pkg for p in state["profiles"] for pkg in PROFILES[p]}
            if name in installed:
                print(f"You are going to remove profile package '{name}'")
            
            uv("remove", name, cwd=root)

    save_state_file(root, state)   

def cmd_list(args):
    root = find_project_root()
    installed = set(load_state_file(root)["profiles"])

    for name, pkg  in PROFILES.items():
        mark = "*" if name in installed else " "
        print(f"{mark} {name:8} {" ,".join(pkg)}")

def cmd_launch_jupyter():
    uv("run", "jupyter", "lab", "--no-browser", "--ip=127.0.0.1", f"--port={JUPYTER_PORT}", "--ServerApp.port_retries=0", f"--IdentityProvider.token={JUPYTER_TOKEN}")
    time.sleep(3)
    webbrowser.open(f"http://127.0.0.1:{JUPYTER_PORT}/lab?token={JUPYTER_TOKEN}")


# MAIN 

def build_parser():
    parser = argparse.ArgumentParser(prog="setup")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create a new project")
    p_init.add_argument("project_name", help="The Name of the initialized project")
    p_init.add_argument("--profile", nargs="+", choices=PROFILES, default=["data"], help="Select which profiles to download")
    p_init.add_argument("--jupyter", action="store_true", help="add Jupyter Packages")
    p_init.set_defaults(func=cmd_init)

    for name, func, helptext in [
        ("add", cmd_add, "Add profiles or packages"),
        ("rm", cmd_rm, "Remove profiles or packages")
    ]:
        p = sub.add_parser(name, help=helptext)
        p.add_argument("targets", nargs="+", help="profile or package names")
        p.add_argument("-y", "--yes", action="store_true", help="accept default, no prompts")
        p.set_defaults(func=func)

    p_list = sub.add_parser("list", help="Show profiles and which are installed")
    p_list.set_defaults(func=cmd_list)

    p_jupyter = sub.add_parser("start", help="Start Jupyter Server and opens it.")
    p_jupyter.set_defaults(func=cmd_launch_jupyter)

    return parser
    
def main():
    args = build_parser().parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
