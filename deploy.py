#!/usr/bin/env python3
#claude go brr


import subprocess
import sys
import os
import json
from pathlib import Path

def run_cmd(cmd, get_output=False):
    print(f"> {cmd}")
    try:
        if get_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"failed: {result.stderr}")
                return None
            return result.stdout.strip()
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0
    except Exception as e:
        print(f"command error: {e}")
        return False

def check_requirements():
    print("checking stuff...")
    
    # check modal cli
    modal_version = run_cmd("modal --version", get_output=True)
    if not modal_version:
        print("modal cli missing. install: pip install modal")
        return False
    
    # check login status
    try:
        result = subprocess.run(["modal", "token", "current"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("not logged in to modal. run: modal token new")
            return False
    except:
        print("modal auth problem. run: modal token new")
        return False
    
    # check main file
    if not Path("app.py").exists():
        print("app.py not found")
        return False
    
    print("everything looks good")
    return True

def build_image():
    print("building modal image...")
    success = run_cmd("modal build app.py")
    if success:
        print("build complete")
    else:
        print("build failed")
    return success

def start_dev():
    print("starting dev server...")
    print("ctrl+c to stop")
    run_cmd("modal serve app.py")

def deploy_prod():
    print("deploying to production...")
    success = run_cmd("modal deploy app.py")
    if success:
        print("deployment successful")
    else:
        print("deployment failed")
    return success

def check_health():
    print("checking service health...")
    output = run_cmd("modal run app.py::health_check", get_output=True)
    if output:
        try:
            data = json.loads(output)
            print(f"service status: {data.get('status')}")
            print(f"pytorch: {data.get('torch_version')}")
            print(f"cuda: {data.get('cuda_available')}")
        except:
            print("service responded but output is weird")
    else:
        print("health check failed")

def cleanup_files(days=7):
    print(f"cleaning up files older than {days} days...")
    success = run_cmd(f"modal run app.py::cleanup_old_files --days-old {days}")
    if success:
        print("cleanup done")
    else:
        print("cleanup failed")

def show_logs():
    print("showing service logs...")
    run_cmd("modal logs kohya-ss-gui")

def list_volumes():
    print("modal volumes:")
    run_cmd("modal volume list")

def print_help():
    print("usage: python deploy.py <command>")
    print("")
    print("commands:")
    print("  dev        start development server")
    print("  prod       deploy to production")
    print("  build      build docker image only")
    print("  health     check if service is running")
    print("  logs       show service logs")
    print("  volumes    list modal volumes")
    print("  cleanup    cleanup old files (default 7 days)")
    print("  check      check requirements")
    print("")
    print("examples:")
    print("  python deploy.py dev")
    print("  python deploy.py cleanup 14")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # check command doesn't need auth
    if command == 'check':
        check_requirements()
        sys.exit(0)
    
    if command == 'help' or command == '-h' or command == '--help':
        print_help()
        sys.exit(0)
    
    # other commands need modal to be setup
    if not check_requirements():
        print("fix requirements first. run: python deploy.py check")
        sys.exit(1)
    
    # run the actual command
    if command == 'build':
        build_image()
    elif command == 'dev':
        start_dev()
    elif command == 'prod':
        deploy_prod()
    elif command == 'health':
        check_health()
    elif command == 'logs':
        show_logs()
    elif command == 'volumes':
        list_volumes()
    elif command == 'cleanup':
        days = 7
        if len(sys.argv) > 2:
            try:
                days = int(sys.argv[2])
            except ValueError:
                print(f"invalid number of days: {sys.argv[2]}, using 7")
        cleanup_files(days)
    else:
        print(f"unknown command: {command}")
        print("run 'python deploy.py help' for usage")
