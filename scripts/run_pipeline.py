#!/usr/bin/env python3
"""Single-command AskBack pipeline for an agent or a human."""

import argparse
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(command):
    print("+", " ".join(str(item) for item in command), flush=True)
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"pipeline stopped at {pathlib.Path(command[1]).name} (exit {exc.returncode})") from exc


def main():
    parser = argparse.ArgumentParser(description="Generate outputs/askback.mp4 from input/")
    parser.add_argument("--input", default="input")
    parser.add_argument("--work", default="work")
    parser.add_argument("--output", default="outputs/askback.mp4")
    parser.add_argument("--model", default=None)
    parser.add_argument("--offline-v08", action="store_true", help="use the checked-in V08 reference storyboard")
    args = parser.parse_args()
    python = sys.executable
    scripts = ROOT / "scripts"
    run([python, str(scripts / "inspect_input.py"), "--input", args.input, "--work", args.work])
    storyboard_command = [python, str(scripts / "generate_storyboard.py"), "--input", args.input, "--work", args.work]
    if args.model:
        storyboard_command += ["--model", args.model]
    if args.offline_v08:
        storyboard_command.append("--offline-v08")
    run(storyboard_command)
    run([python, str(scripts / "generate_tts.py"), "--storyboard", str(pathlib.Path(args.work) / "storyboard.json"), "--workdir", args.work])
    run([python, str(scripts / "render_video.py"), "--storyboard", str(pathlib.Path(args.work) / "storyboard.json"), "--workdir", args.work, "--output", args.output])
    run([python, str(scripts / "validate_output.py"), args.output])


if __name__ == "__main__":
    main()
