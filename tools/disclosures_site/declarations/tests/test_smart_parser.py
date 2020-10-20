import os
import sys
import time
import subprocess
import shutil

class SmartParserServerForTesting:

    def __init__(self, workdir, folder):
        self.server = None
        self.folder = folder
        self.workdir = workdir

    def __enter__(self):
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir)
        os.mkdir(self.workdir)
        tool_dir = os.path.join(os.path.dirname(__file__), "../../../robots/dlrobot/scripts/cloud")
        server_script = os.path.join(tool_dir, "smart_parser_cache.py")
        assert os.path.exists (server_script)
        self.server = subprocess.Popen(
            ['/usr/bin/python3',
               server_script,
               #'--worker-count', '1'
             ],
            stdout=sys.stdout,
            stderr=sys.stderr,
            env=os.environ,
            cwd=self.workdir
            )
        time.sleep(1)

        client = subprocess.Popen(
            ['/usr/bin/python3',
               os.path.join(tool_dir, "smart_parser_cache_client.py"),
              '--walk-folder-recursive',
              self.folder,
             '--action',
             'put',
             '--timeout',
             '1'
             ],
            stdout=subprocess.PIPE,
            #stderr=subprocess.PIPE,
            stderr=sys.stderr,
            env=os.environ,
            )
        client.wait()
        time.sleep(4) # normally we should ask the server in cycle till it finishes

    def __exit__(self, exc_type, exc_value, traceback):
        if self.server is not None:
            self.server.kill()