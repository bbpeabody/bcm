import sublime
import sublime_plugin

import subprocess
import threading
import os
import re
import signal

class FwBuildCommand(sublime_plugin.WindowCommand):

    encoding = 'utf-8'
    killed = False
    proc = None
    panel = None
    panel_lock = threading.Lock()
    THOR_MAKE_PATH = 'main/Cumulus/firmware/THOR'
    CHIMP_MAKE_PATH = 'main/Cumulus/firmware/ChiMP/bootcode'

    def is_enabled(self, lint=False, integration=False, kill=False):
        # The Cancel build option should only be available
        # when the process is still running
        if kill:
            return self.proc is not None and self.proc.poll() is None
        return True

    def run(self, chip="thor", build_type="release", kill=False):
        self._docker_netxtreme_path = None
        self._local_make_path = None
        self._netxtreme_path = None
        self.chip = chip
        if kill:
            if self.proc:
                self.killed = True
                self.proc.communicate(input=b'\x03')
                self.proc.terminate()
            return

        vars = self.window.extract_variables()
        try:
            self.working_dir = vars['file_path']
        except KeyError as err:
            sublime.error_message("You need to open a file, so I know what repo you want to build.")
            raise err

        #working_dir = "/"

        # A lock is used to ensure only one thread is
        # touching the output panel at a time
        with self.panel_lock:
            # Creating the panel implicitly clears any previous contents
            self.panel = self.window.create_output_panel('exec')

            # Enable result navigation. The result_file_regex does
            # the primary matching, but result_line_regex is used
            # when build output includes some entries that only
            # contain line/column info beneath a previous line
            # listing the file info. The result_base_dir sets the
            # path to resolve relative file names against.
            settings = self.panel.settings()
            settings.set(
                'result_file_regex',
                r'^(\S+):(\d+):(\d+):\s*(.*)'
            )
            #settings.set(
            #    'result_line_regex',
            #    r'^\s+line (\d+) col (\d+)'
            #)
            settings.set('result_base_dir', self.working_dir)

            self.window.run_command('show_panel', {'panel': 'output.exec'})

        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

        args = ['/Users/bpeabody/git/bcm/scripts/docker_make.sh']
        args.append('-d')
        args.append(self.docker_netxtreme_path)
        args.append('--signed')
        if chip == "thor" or chip == "chimp":
            args.append(chip)
        else:
            error_msg = "Invalid chip type {chip}".format(chip=chip)
            sublime.error_message(error_msg)
            raise ValueError(error_msg)
        if build_type == "release" or build_type == "debug" or build_type == "clean":
            args.append(build_type)
        else:
            error_msg = "Invalid build type {build_type}".format(build_type=build_type)
            sublime.error_message(error_msg)
            raise ValueError(error_msg)
        self.proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.working_dir
        )
        self.killed = False

        threading.Thread(
            target=self.read_handle,
            args=(self.proc.stdout,)
        ).start()

    def read_handle(self, handle):
        chunk_size = 2 ** 10
        out = b''
        while True:
            try:
                data = os.read(handle.fileno(), chunk_size)
                # If exactly the requested number of bytes was
                # read, there may be more data, and the current
                # data may contain part of a multibyte char
                out += data
                if len(data) == chunk_size:
                    continue
                if data == b'' and out == b'':
                    raise IOError('EOF')
                # We pass out to a function to ensure the
                # timeout gets the value of out right now,
                # rather than a future (mutated) version
                self.queue_write(out.decode(self.encoding))
                if data == b'':
                    raise IOError('EOF')
                out = b''
            except (UnicodeDecodeError) as e:
                msg = 'Error decoding output using %s - %s'
                self.queue_write(msg  % (self.encoding, str(e)))
                break
            except (IOError):
                if self.killed:
                    msg = 'Cancelled'
                else:
                    msg = 'Finished'
                self.queue_write('\n[%s]' % msg)
                break

    def queue_write(self, text):
        sublime.set_timeout(lambda: self.do_write(text), 30)

    def do_write(self, text):
        text = self.translate_file_paths(text)
        with self.panel_lock:
            self.panel.run_command('append', {'characters': text})

    def translate_file_paths(self, text):
        regexs = [
            # Example: ../Primate/grc.c:561:9: error: 'ELAS_PR_TMR_PRIORITY' undeclared (first use in this function)
            r"(?P<before>^)(?P<filename>\S+)(?P<after>:\d+:\d+:\s+.*)",
            # Example: Compiling: ../Primate/main_srt.c
            r"(?P<before>^Compiling:\s+)(?P<filename>\S+)(?P<after>.*)",
            # Example: ../Primate/grc.c: In function 'grc_hisr_func':
            r"(?P<before>^)(?P<filename>\S+)(?P<after>\s+In function .*)",
            # Example: Linking: THORB0_DUAL_SIGNED_0001_0001/srt_bootcode.out
            r"(?P<before>^Linking:\s*)(?P<filename>\S+)(?P<after>.*)",
            # Example: Generating THORB0_DUAL_SIGNED_0001_0001/srt.bin file
            r"(?P<before>^Generating\s+)(?P<filename>\S+)(?P<after>.*)",
            # Example: Created THORB0_DUAL_SIGNED_0001_0001/srt_thor.signed.rev0001.bin
            r"(?P<before>^Created\s+)(?P<filename>\S+)(?P<after>.*)",
        ]
        new_lines = []
        for line in text.splitlines():
            line = line.rstrip('\r\n')
            for regex in regexs:
                match = re.search(regex, line)
                if match:
                    new_filename = self.translate_path(match.group("filename"))
                    line = match.group("before") + new_filename + match.group("after")
                    break
            new_lines.append(line + '\n')
        return ''.join(new_lines)

    def translate_path(self, path):
        return os.path.abspath(os.path.join(self.local_make_path, path))

    @property
    def netxtreme_path(self):
        if self._netxtreme_path is None:
            match = re.search(r"^.*/(netxtreme[^\/]*).*", self.working_dir)
            if match:
                self._netxtreme_path = match.group(1)
            else:
                sublime.error_message("Cannot find string netxtreme in {working_dir}".format(working_dir=self.working_dir))
                raise ValueError()
        return self._netxtreme_path

    @property
    def docker_netxtreme_path(self):
        if self._docker_netxtreme_path is None:
            parts = self.working_dir.split(self.netxtreme_path)
            # Translate /Users/bpeabody (macOS) to /home/bpeabody (linux)
            # It's assumed that the netxtreme repo is cloned to your home directory
            self._docker_netxtreme_path = parts[0].replace("/Users/", "/home/") + self.netxtreme_path + '/'
        return self._docker_netxtreme_path

    @property
    def local_make_path(self):
        if self._local_make_path is None:
            parts = self.working_dir.split(self.netxtreme_path)
            # Translate /Users/bpeabody (macOS) to /home/bpeabody (linux)
            # It's assumed that the netxtreme repo is cloned to your home directory
            netxtreme = parts[0] + self.netxtreme_path + '/'
            if self.chip == "thor":
                self._local_make_path = netxtreme + self.THOR_MAKE_PATH
            elif self.chip == "chimp":
                self._local_make_path = netxtreme + self.CHIMP_MAKE_PATH
            else:
                raise ValueError("Unsupported chip {chip}".format(chip=self.chip))
        return self._local_make_path

