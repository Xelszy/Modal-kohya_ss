#!/usr/bin/env python3
#claude go brr

import subprocess
import sys
import os
import json
from pathlib import Path

# pastikan stdout pakai UTF-8
sys.stdout.reconfigure(encoding="utf-8")


def safe_print(msg: str):
    """Print tanpa error unicode (ganti karakter aneh jadi '?')."""
    if msg is None:
        return
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode())


def run_cmd(cmd, get_output=False):
    safe_print(f"> {cmd}")
    try:
        if get_output:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            if result.returncode != 0:
                safe_err = result.stderr.encode("ascii", "replace").decode()
                safe_print(f"failed: {safe_err}")
                return None
            return result.stdout.strip()
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0
    except Exception as e:
        safe_print(f"command error: {e}")
        return False


def check_requirements():
    safe_print("checking stuff...")

    # check modal cli
    modal_version = run_cmd("modal --version", get_output=True)
    if not modal_version:
        safe_print("modal cli missing. install: pip install modal")
        return False

    # check login status
    try:
        result = subprocess.run(
            ["modal", "config", "show", "--redact"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            safe_print("not logged in to modal. run: modal token new")
            return False
    except:
        safe_print("modal auth problem. run: modal token new")
        return False

    # check main file
    if not Path("app.py").exists():
        safe_print("app.py not found")
        return False

    safe_print("everything looks good")
    return True


def build_image():
    safe_print("building modal image...")
    success = run_cmd("modal build app.py")
    if success:
        safe_print("build complete")
    else:
        safe_print("build failed")
    return success


def start_dev():
    safe_print("starting dev server...")
    safe_print("ctrl+c to stop")
    run_cmd("modal serve app.py")


def deploy_prod():
    safe_print("deploying to production...")
    success = run_cmd("modal deploy app.py")
    if success:
        safe_print("deployment successful")
    else:
        safe_print("deployment failed")
    return success


def check_health():
    safe_print("checking service health...")
    output = run_cmd("modal run app.py::health_check", get_output=True)
    if output:
        try:
            data = json.loads(output)
            safe_print(f"service status: {data.get('status')}")
            safe_print(f"pytorch: {data.get('torch_version')}")
            safe_print(f"cuda: {data.get('cuda_available')}")
        except Exception as e:
            safe_print("service responded but not valid JSON:")
            safe_print(output)
    else:
        safe_print("health check failed")


def cleanup_files(days=7):
    safe_print(f"cleaning up files older than {days} days...")
    success = run_cmd(f"modal run app.py::cleanup_old_files --days-old {days}")
    if success:
        safe_print("cleanup done")
    else:
        safe_print("cleanup failed")


def show_logs():
    safe_print("showing service logs...")
    run_cmd("modal logs kohya-ss-gui")


def list_volumes():
    safe_print("modal volumes:")
    run_cmd("modal volume list")


def print_help():
    safe_print("usage: python deploy.py <command>")
    safe_print("")
    safe_print("commands:")
    safe_print("  dev        start development server")
    safe_print("  prod       deploy to production")
    safe_print("  build      build docker image only")
    safe_print("  health     check if service is running")
    safe_print("  logs       show service logs")
    safe_print("  volumes    list modal volumes")
    safe_print("  cleanup    cleanup old files (default 7 days)")
    safe_print("  check      check requirements")
    safe_print("")
    safe_print("examples:")
    safe_print("  python deploy.py dev")
    safe_print("  python deploy.py cleanup 14")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    command = sys.argv[1].lower()

    # check command doesn't need auth
    if command == "check":
        check_requirements()
        sys.exit(0)

    if command in ("help", "-h", "--help"):
        print_help()
        sys.exit(0)

    # other commands need modal to be setup
    if not check_requirements():
        safe_print("fix requirements first. run: python deploy.py check")
        sys.exit(1)

    # run the actual command
    if command == "build":
        build_image()
    elif command == "dev":
        start_dev()
    elif command == "prod":
        deploy_prod()
    elif command == "health":
        check_health()
    elif command == "logs":
        show_logs()
    elif command == "volumes":
        list_volumes()
    elif command == "cleanup":
        days = 7
        if len(sys.argv) > 2:
            try:
                days = int(sys.argv[2])
            except ValueError:
                safe_print(f"invalid number of days: {sys.argv[2]}, using 7")
        cleanup_files(days)
    else:
        safe_print(f"unknown command: {command}")
        safe_print("run 'python deploy.py help' for usage")
