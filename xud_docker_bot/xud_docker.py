import os
from subprocess import check_output, PIPE, STDOUT, CalledProcessError
import logging
import shutil
import re
from requests import get

# TODO dynamically generate this image_tags map
image_tags = {
    "bitcoind": ["0.20.0"],
    "litecoind": ["0.18.1"],
    "geth": ["1.9.16"],
    "lnd": ["0.10.2-beta", "0.10.2-beta-simnet", "0.10.1-beta-ltc", "0.10.1-beta-ltc-simnet"],
    "connext": ["latest", "7.0.0-alpha.14"],
    "xud": ["latest", "1.0.0-beta.5"],
    "arby": ["latest", "0.2.0"],
    "boltz": ["latest", "1.0.0"],
    "webui": ["latest", "1.0.0"],
    "utils": ["latest"],
}


class XudDockerRepo:
    def __init__(self, repo_dir):
        self.logger = logging.getLogger("xud_docker_bot.XudDockerRepo")
        self.repo_dir = repo_dir
        repo_url = "https://github.com/ExchangeUnion/xud-docker.git"
        self._ensure_repo(repo_url, self.repo_dir)

    def _clone_repo(self, repo_url, repo_dir):
        self._execute(f"git clone {repo_url} {repo_dir}")

    def _execute(self, cmd):
        output = check_output(cmd, shell=True, stderr=STDOUT)
        self.logger.debug("$ %s\n%s", cmd, output.decode())

    def _get_origin_url(self):
        cmd = f"git remote get-url origin"
        output = check_output(cmd, shell=True, stderr=PIPE)
        output = output.decode()
        self.logger.debug("$ %s\n%s", cmd, output)
        return output.strip()

    def _check(self, repo_url, repo_dir):
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            return False
        wd = os.getcwd()
        try:
            os.chdir(repo_dir)
            try:
                self._execute(f"git status")
            except CalledProcessError:
                return False

            return self._get_origin_url() == repo_url
        finally:
            os.chdir(wd)

    def _ensure_repo(self, repo_url, repo_dir):
        if not self._check(repo_url, repo_dir):
            if os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)

        if not os.path.exists(repo_dir):
            self._clone_repo(repo_url, repo_dir)

    def get_affected_branches(self, image, branch):
        # FIXME get all branches in xud-docker which are affected by upstream branch changes
        # branches = filter_merged_branches(branches)
        if branch == "master":
            return ["master"]
        else:
            return []

    def get_pr(self, branch):
        try:
            r = get(f"https://api.github.com/repos/exchangeunion/xud-docker/pulls?head=exchangeunion:{branch}")
            j = r.json()
            if len(j) == 0:
                return None
            elif len(j) == 1:
                return j[0]
            elif len(j) > 1:
                raise RuntimeError("There are multiple PRs related to branch {}".format(branch))
        except:
            pass
        return None

    def filter_merged_branches(self, branches):
        result = []
        for b in branches:
            if b == "master":
                result.append(b)
                continue
            pr = self.get_pr(b)
            if pr and pr["state"] == "open":
                result.append(b)

        return result

    def get_modified_images(self, branch):
        wd = os.getcwd()
        try:
            os.chdir(self.repo_dir)
            self._execute("git checkout master")
            self._execute("git fetch")
            try:
                self._execute(f"git branch -D {branch}")
            except CalledProcessError:
                pass
            self._execute(f"git checkout {branch}")
            self._execute(f"git pull origin {branch}")

            if branch == "master":
                commit = "0aa9c74f46012d212134ec6b7d58732b84f14ee0"
            else:
                commit = "master"

            cmd = "git diff --name-only {} -- images".format(commit)
            output = check_output(cmd, shell=True, stderr=PIPE)
            output = output.decode()
            self.logger.debug("$ %s\n%s", cmd, output)
            lines = output.splitlines()
            images = set()
            p = re.compile(r"^images/([^/]+)/.+$")
            for line in lines:
                m = p.match(line)
                if m:
                    images.add(m.group(1))
            self.logger.debug("Modified images: %s", images)
            result = []
            for image in images:
                result.extend([f"{image}:{tag}" for tag in image_tags[image]])
            self.logger.debug("Rebuilt tags: %s", result)
            return result
        finally:
            os.chdir(wd)
