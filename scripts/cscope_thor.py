#!/usr/bin/env python3

"""
Script to generate cscope cross-reference files.  Specifically for THOR, but can be used generically as well.

If Thor firmware has been built and the build artifacts exist, then the dependency files generated by gcc with
extension .d will be used for input to cscope.  This is very fast.  The resulting cross-reference list is compact with
only files tagged that Thor builds.  Thus, eliminating much of the noise from other source that Thor does not use.

If there is no Thor build, then the script defaults to tagging every source file in the repo. In this mode, the script
can be used in any repo to create a complete cross-reference of all C source.

The script operates on the current directory.  It must be inside a git repo.  The entire repo will be indexed and the
output files will be placed at the root directory of the repo.

The script is standalone and should run on any python version 3.4+. It uses only standard python modules that should be
available in any vanilla python installation.

Prerequisites:
  - git executable installed
  - cscope executable installed
  - git repo cloned

Usage:
  cd <git_repo>
  cscope_thor.py

Script generates four files at the root of the repo:
  - cscope.files: List of source files used by cscope
  - cscope.out: Symbol cross-reference file
  - cscope.in.out and
    cscope.po.out: Inverted index files used for quick symbol searching

author: brad.peabody@broadcom.com
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from subprocess import run, PIPE, Popen
from time import time

MIN_PYTHON = (3, 4)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

THOR_DIR = os.path.join('main', 'Cumulus', 'firmware', 'THOR')
THOR_OBJ_DIR = 'obj'
GIT_BIN = ['git', '--no-pager']
CSCOPE_FILE = "cscope.files"
CSCOPE_BIN = "cscope"
CSCOPE_OUT = [
    'cscope.out',
    'cscope.in.out',
    'cscope.po.out'
]
SOURCE_EXT = [
    'c',
    'h',
    'C',
    'H'
]


def repo_root():
    """
    Return the root directory of the repo. git binary must be installed on system.
    """
    cmd = GIT_BIN + ['rev-parse', '--path-format=relative', '--show-toplevel']
    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    except FileNotFoundError:
        print("ERROR: git binary is not installed.")
        sys.exit(1)
    p.wait(5)
    output = p.stdout.read().decode()
    if p.returncode == 0:
        rel_path = output.strip()
        pwd = os.getenv('PWD')
        return os.path.normpath(os.path.join(pwd, rel_path))
    print("ERROR: Not in a git repo.")
    sys.exit(1)


def get_dependency_files(obj_dir):
    """
    Searches for dependency files that were created by Thor build. These files end with .d extension and are
    located in the obj dir in the THOR firmware folder. Returns empty list if Thor has not been built.
    """
    files = []
    if os.path.isdir(obj_dir):
        for path in os.listdir(obj_dir):
            if path.startswith('crt') or path.startswith('srt'):
                files.extend(list(Path(os.path.join(obj_dir, path)).rglob("*.d")))
    return files


def get_dependencies(thor_dir, files):
    """
    Parses the list of files for dependencies listed in the files.  Returns a set of files that the SRT/CRT build used.

    :param thor_dir: Thor firmware directory where the make scripts are located.
                     i.e. /<repo_root>/main/Cumulus/firmware/THOR
    :param files: List of *.d files. Absolute paths.
    :return: Set of source files (*.c and *.h) used by build with absolute paths.
    """
    deps = set()
    for file in files:
        with open(file, "r") as f:
            contents = f.read()
        words = contents.split()
        for word in words:
            for ext in SOURCE_EXT:
                if word.endswith(f".{ext}"):
                    deps.add(os.path.normpath(os.path.join(thor_dir, word)))
                    break
    return deps


def get_all_source_files(dir):
    """
    Searches for all source files ending with .h, .c, .H, or .C.

    :param dir: top-level dir to begin recursive search for source files.
    :return: List of source files (*.c and *.h) with absolute paths.
    """
    files = []
    glob_pattern = "*.[" + ''.join(SOURCE_EXT) + "]"
    if os.path.isdir(dir):
        files = list(Path(dir).rglob(glob_pattern))
    # exclude symlinks from file list
    files = [p for p in files if not p.is_symlink()]
    return [str(p) for p in files]


def write_cscope_file_list(files, cscope_file):
    """
    Writes the cscope file list.

    :param files: List of files to be written
    :param cscope_file: File name to write to
    """
    print(f"cscope file list is here: {cscope_file}")
    with open(cscope_file, "w") as f:
        f.writelines([f'"{l}"\n' for l in files])


def get_cscope_version():
    """
    Return the version of the cscope binary. Exits if system call fails.
    """
    p = Popen([CSCOPE_BIN, '--version'], stdout=PIPE, stderr=PIPE)
    p.wait(5)
    output = p.stderr.read().decode()
    if p.returncode == 0:
        match = re.search(r'version\s+(\S+)', output)
        if match:
            return match.group(1)
    print("ERROR: cscope binary not found.")
    sys.exit(1)


def run_cscope(repo_root_dir):
    """
    Executes the cscope binary and builds the cross-reference files. It is assumed that the file list with the default
    name of cscope.files already exists in the repo_root directory.

    :param repo_root_dir: Root directory of the repo
    """
    print(f"Running {CSCOPE_BIN}.")
    os.chdir(repo_root_dir)
    p = run([CSCOPE_BIN, '-bkq'])
    if p.returncode == 0:
        for file in CSCOPE_OUT:
            file = os.path.join(repo_root_dir, file)
            if not os.path.exists(file):
                print(f"ERROR: Failed to create {CSCOPE_BIN} output file {file}.")
                sys.exit(1)
            else:
                print(f"{CSCOPE_BIN} generated {file}")
    else:
        print(f"ERROR: {CSCOPE_BIN} failed. Returned {p.returncode}.")
        sys.exit(1)


if __name__ == "__main__":
    start = time()
    # Check that cscope binary is installed.
    cscope_version = get_cscope_version()
    print(f"Using {CSCOPE_BIN} version {cscope_version}.")
    # Check that we're inside a git repo and determine the root directory of the repo.
    repo_dir = repo_root()
    thor_dir = os.path.join(repo_dir, THOR_DIR)
    thor_obj_dir = os.path.join(thor_dir, THOR_OBJ_DIR)
    cscope_file = os.path.join(repo_dir, CSCOPE_FILE)
    files = []
    use_make_deps = True
    for dir in [thor_dir, thor_obj_dir]:
        if not os.path.isdir(dir):
            print(f"{dir} does not exist. All files will be tagged - not just Thor.")
            use_make_deps = False
            break
    if use_make_deps:
        dependency_files = get_dependency_files(thor_obj_dir)
        if not dependency_files:
            print(f"Did not find any dependency files (*.d) in {thor_obj_dir}. All files will be tagged - not just Thor.")
        else:
            print(f"Tagging Thor build dependencies found here: {thor_obj_dir}")
            files = sorted(get_dependencies(thor_dir, dependency_files))
    if not files:
        print(f"Tagging all source files found here: {repo_dir}")
        files = sorted(get_all_source_files(repo_dir))
    write_cscope_file_list(files, cscope_file)
    run_cscope(repo_dir)
    end = time()
    print(f"Finished in {end - start:.1f} seconds.")

