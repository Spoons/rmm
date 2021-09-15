import subprocess
from functools import partial

cmd_run = partial(subprocess.Popen, text=True, shell=True)


def is_child(pid, child_pid):
    '''
    check whether child_pid is a child of pid
    '''
    tree = cmd_output(f'pstree -T -p {pid}')
    for line in tree.split('\n'):
        if child_pid in line:
            return True
        return False


def execute(cmd):
    with subprocess.Popen(cmd, stdout=subprocess.PIPE,
                          universal_newlines=True, text=True, close_fds=True, shell=True) as proc:
        for line in iter(proc.stdout.readline, b''):
            yield line
            if (r:= proc.poll()) is not None:
                if r != 0: raise subprocess.CalledProcessError(r, cmd)
                break


def cmd_output(cmd):
    '''
    subprocess's check output with some defaults and exception handling
    '''
    try:
        out = subprocess.check_output(cmd, text=True, shell=True).strip()
    except Exception:
        out = ''
        return out

