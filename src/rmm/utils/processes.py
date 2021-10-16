import subprocess
from functools import partial

cmd_run = partial(subprocess.Popen, text=True, shell=True)


def execute(cmd):
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        text=True,
        close_fds=True,
        shell=True,
    ) as proc:
        for line in iter(proc.stdout.readline, b""):
            yield line
            if (r := proc.poll()) is not None:
                if r != 0:
                    raise subprocess.CalledProcessError(r, cmd)
                break


def run_sh(cmd):
    subprocess.check_output(cmd, text=True, shell=True).strip()
