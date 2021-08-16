#!/usr/bin/env python3
import paramiko
import os
import multiprocessing as mp
import time

LOCAL_PKG = "/Users/bpeabody/git/netxtreme/main/Cumulus/firmware/THOR/THORB0_SIGNED_0001/thor.signed.crid0001.pkg"
SIT = "218.1.25.0"

SHAPER = {
    "addr": "10.27.215.99",
    "username": "root",
    "password": "brcm",
    "bnxtmt_device": 3,
}

DOMINO = {
    "addr": "10.27.215.84",
    "username": "root",
    "password": "brcm",
    "bnxtmt_device": 3,
}

RAIL = {
    "addr": "10.27.23.244",
    "username": "root",
    "password": "brcm",
    "bnxtmt_device": 3,
}

STILE = {
    "addr": "10.27.23.236",
    "username": "root",
    "password": "brcm",
    "bnxtmt_device": 3,
}

def connect(hostname, username, password, port=22):
    s = paramiko.SSHClient()
    s.load_system_host_keys()
    s.connect(hostname, port, username, password)
    return s


def exec(conn, command):
    lines = []
    stdin, stdout, stderr = conn.exec_command(command)
    for line in stdout.readlines():
        lines.append(line.strip())
    return lines

def get_remote_bnxtmt_dir(conn, sit_dir):
    lines = exec(conn, f"ls {sit_dir}")
    for line in lines:
        if line.startswith("bnxtmt"):
            return os.path.join(sit_dir, line)
    raise FileNotFoundError(f"Cannot find bnxtmt directory in {sit_dir}")


def get_remote_bnxt_en(conn, sit_dir):
    lines = exec(conn, f"ls {sit_dir}")
    bnxt_en = None
    for line in lines:
        if line.startswith("bnxt_en"):
            bnxt_en = os.path.join(sit_dir, line, "bnxt_en.ko")
            break
    if bnxt_en is None:
        raise FileNotFoundError(f"Cannot find bnxt_en directory in {sit_dir}")
    sftp = conn.open_sftp()
    try:
        sftp.stat(bnxt_en)
    except IOError:
        raise IOError(f"Remote file {bnxt_en} does not exist on {hostname}")
    sftp.close()
    return bnxt_en


def copy_to_remote(conn, local_file, remote_file):
    sftp = conn.open_sftp()
    sftp.put(local_file, remote_file)
    sftp.close()


def get_wget_sit_path():
    my_dir = os.path.dirname(os.path.realpath(__file__))
    wget_sit = os.path.join(my_dir, "wget_sit")
    if not os.path.exists(wget_sit):
        raise FileNotFoundError(f"{wget_sit} does not exist.")
    return wget_sit


def get_sit_dir(conn, sit_version):
    lines = exec(conn, "echo $HOME")
    home_dir = lines[0]
    lines = exec(conn, f"ls {home_dir}")
    for line in lines:
        if line == sit_version:
            return os.path.join(home_dir, line)
    # SIT package not found, so go and get it.
    wget_sit_local = get_wget_sit_path()
    wget_sit_remote = os.path.join(home_dir, "wget_sit")
    copy_to_remote(conn, wget_sit_local, wget_sit_remote)
    exec(conn, f"chmod +x {wget_sit_remote}")
    exec(conn, f"{wget_sit_remote} -b {sit_version}")
    sit_dir = os.path.join(home_dir, sit_version)
    sftp = conn.open_sftp()
    try:
        sftp.stat(sit_dir)
    except IOError:
        raise IOError(f"Remote sit directory {sit_dir} does not exist.")
    return sit_dir


def get_remote_pkg_filename(conn):
    home_dir = exec(conn, "echo $HOME")[0]
    return os.path.join(home_dir, os.path.basename(LOCAL_PKG))


def load_driver(conn):
    sit_dir = get_sit_dir(conn, SIT)
    driver = get_remote_bnxt_en(conn, sit_dir)
    exec(conn, f"modprobe devlink")
    exec(conn, f"insmod {driver}")


def unload_driver(conn):
    lines = exec(conn, "lsmod")
    driver_loaded = False
    for line in lines:
        if line.startswith("bnxt_en"):
            driver_loaded = True
            break
    if driver_loaded:
        exec(conn, "rmmod bnxt_en")


def install_pkg(conn, device):
    sit_dir = get_sit_dir(conn, SIT)
    bnxt_mt_dir = get_remote_bnxtmt_dir(conn, sit_dir)
    remote_pkg = get_remote_pkg_filename(conn)
    channel = conn.invoke_shell()
    stdin = channel.makefile('wb')
    stdout = channel.makefile('rb')
    stdin.write(f'''
    cd {bnxt_mt_dir}
    ./load.sh -eval "device {device}; nvm pkginstall {remote_pkg} -noidcheck; reset all"
    exit
    ''')
    failed = True
    for line in stdout.readlines():
        line = line.decode("utf-8").lower()
        if "failure" in line or "failed" in line:
            failed = True
            break
        if "clearing fastboot registers" in line:
            failed = False

    if failed:
        raise IOError("Failed to install package.")
    stdout.close()
    stdin.close()


def ports_up(conn):
    time.sleep(1)
    exec(conn, "ip link set up p1p1")
    exec(conn, "ip link set up p1p2")


def update(hostname, username, password, device):
    conn = connect(hostname, username, password)
    print(f"{hostname}: Unloading bnxt_en driver")
    unload_driver(conn)
    remote_pkg = get_remote_pkg_filename(conn)
    print(f"{hostname}: SFTP {LOCAL_PKG} to {remote_pkg}")
    copy_to_remote(conn, LOCAL_PKG, remote_pkg)
    print(f"{hostname}: Installing package with bnxtmt")
    install_pkg(conn, device)
    print(f"{hostname}: Loading bnxt_en driver")
    load_driver(conn)
    print(f"{hostname}: Bringing ports up.")
    ports_up(conn)

if __name__ == '__main__':
    processes = []
    #for server in [DOMINO, SHAPER]:
    for server in [RAIL, STILE]:
        p = mp.Process(target=update, args=(server["addr"],
                                            server["username"],
                                            server["password"],
                                            server["bnxtmt_device"]))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

