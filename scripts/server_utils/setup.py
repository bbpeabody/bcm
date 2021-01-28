from setuptools import setup, find_packages
import os
import sys

do_server_install = False
if int(os.environ.get("SERVER_UTILS_RPYC_SERVER", 0)):
    do_server_install = True


def read_file(name):
    with open(name, encoding="utf-8") as file:
        return file.read().strip()


def read_lines(name):
    with open(name, encoding="utf-8") as file:
        return file.readlines()


def requirements_without_versions():
    if do_server_install:
        lines = read_lines('requirements_rpyc_server.txt')
    else:
        lines = read_lines('requirements.txt')
    return [line.split('=')[0] for line in lines]


def scripts():
    if do_server_install:
        # Do not install any scripts in the RPyC server's venv/bin
        return []
    # These scripts will be installed in the venv/bin directory
    script_path = './scripts'
    return [os.path.join(script_path, x) for x in os.listdir(script_path)]


def get_hwrm_requirement():
    requirements = []
    # Artifactory URL
    ar_url = 'https://nxt-ci-bots:nxt-ci-bots@artifactory-lvn.broadcom.net/artifactory/api/pypi/pypi-release-local/'

    # Control source of HWRM repo and version by setting environment variables HWRM_SRC and HWRM_VER
    hwrm_src = os.environ.get('HWRM_SRC', 'GL').lower()
    hwrm_ver = os.environ.get('HWRM_VER', '0.5.24')

    if hwrm_src == 'gl' or hwrm_src == 'gitlab':
        requirements += [
            'hwrm_code_gen @ git+http://gitlab-ccxsw.lvn.broadcom.net/aurora/hwrm_code_gen.git',
        ]
    elif hwrm_src == 'ar' or hwrm_src == 'artifactory':
        requirements += [
            f'hwrm_code_gen>={hwrm_ver}',
        ]
    elif hwrm_src == 'ar_fixed' or hwrm_src == 'artifactory_fixed':
        requirements += [
            f'hwrm_code_gen @ {ar_url}hwrm-code-gen/{hwrm_ver}/hwrm_code_gen-{hwrm_ver}.tar.gz',
        ]
    else:
        sys.exit(f"Unexpected value of environment variable HWRM_SRC: {hwrm_src}. Please use one of GL, AR, AR_FIXED.")
    return requirements


version = read_file('VERSION')

requirements = requirements_without_versions()\
# Do not install HWRM repo on RPyC server
if not do_server_install:
    requirements += get_hwrm_requirement()

setup(
    name='server_utils',
    python_requires='>=3.6',
    version=version,
    packages=find_packages(),
    description='Server utility scripts.',
    author='Brad Peabody',
    author_email='brad.peabody@broadcom.com',
    data_files=[('VERSION', ['VERSION']),
                ('config_default.yaml', ['server_utils/config_default.yaml'])],
    install_requires=requirements,
    scripts=scripts(),
    include_package_data=True
)
