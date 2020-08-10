import os
from subprocess import Popen, PIPE, STDOUT, CalledProcessError
import logging
import shutil
from requests import get
from typing import List, Dict, Tuple
from collections import namedtuple
from contextlib import contextmanager

from xud_docker_bot.utils import execute
from xud_docker_bot.clients import DockerhubClient

SCRIPT = """\
from launcher.config.template import nodes_config

def print_network(network):
    for key, value in nodes_config[network].items():
        print("%s/%s %s" % (network, key, value["image"]))

print_network("simnet")
print_network("testnet")
print_network("mainnet")
"""


DOCKERFILE = """\
FROM python:3.8-alpine
RUN pip install docker toml demjson pyyaml
WORKDIR /opt
ADD launcher launcher
"""


VersionChange = namedtuple("ImageChange", ["network", "old_version", "new_version"])
GitReference = namedtuple("GitReference", ["ref", "revision", "commit_message"])

@contextmanager
def workspace(dir):
    wd = os.getcwd()
    try:
        os.chdir(dir)
        yield
    finally:
        os.chdir(wd)


class XudDockerRepo:
    def __init__(self, repo_dir, dockerhub_client: DockerhubClient):
        self._logger = logging.getLogger("xud_docker_bot.XudDockerRepo")
        self.repo_dir = repo_dir
        self.dockerhub_client = dockerhub_client
        repo_url = "https://github.com/ExchangeUnion/xud-docker.git"
        self._ensure_repo(repo_url, self.repo_dir)

    def _clone_repo(self, repo_url, repo_dir):
        try:
            execute(f"git clone {repo_url} {repo_dir}")
        except Exception as e:
            raise RuntimeError("Failed to clone repository %s to folder %s" %(repo_url, repo_dir)) from e

    def _get_origin_url(self):
        try:
            output = execute(f"git remote get-url origin")
            return output.strip()
        except Exception as e:
            raise RuntimeError("Failed to get origin URL") from e

    def _check(self, repo_url, repo_dir):
        if not os.path.exists(repo_dir) or not os.path.isdir(repo_dir):
            return False
        with workspace(repo_dir):
            return self._get_origin_url() == repo_url

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

    def _diff_image_with_revision(self, image, revision) -> bool:
        cmd = f"git diff --name-status {revision} -- images/{image}"
        output = execute(cmd)
        lines = output.splitlines()
        if len(lines) > 0:
            self._logger.debug("Image %s is different from %s\n%s", image, revision, "\n".join(lines))
            return True
        else:
            return False

    def _ensure_utils_dockerfile(self):
        dockerfile = os.path.expanduser("~/.xud-docker-bot/utils.Dockerfile")
        with open(dockerfile, "w") as f:
            f.write(DOCKERFILE)
        return dockerfile

    def _utils_exists(self, revision) -> bool:
        filter = f"reference=utils:{revision}"
        format = "{{.ID}}"
        output = execute(f"docker images --filter='{filter}' --format '{format}'")
        lines = output.splitlines()
        if len(lines) == 1:
            return True
        elif len(lines) == 0:
            return False
        else:
            raise RuntimeError("There shouldn't be multiple utils images with filter: " + filter)

    def _build_utils(self, revision) -> str:
        dockerfile = self._ensure_utils_dockerfile()
        tag = f"utils:{revision}"
        # if self._utils_exists(revision):
        #     self._logger.debug("Skip building utils:%s (existed)", revision)
        #     return tag
        self._checkout_revision(revision)
        with workspace("images/utils/"):
            try:
                execute(f"docker build . -f {dockerfile} -t {tag}")
            except CalledProcessError as e:
                self._logger.error("Failed to build utils:%s\n$ %s\n%s", revision, e.cmd, e.output.decode().strip())
            return tag

    def _dump_template(self, utils_image) -> Dict[str, str]:
        """Dump utils image template.py as a Dict.
        The key is like "simnet/lndbtc"
        The value is like "exchangeunion/lnd:0.10.2-beta-simnet"
        """
        cmd = f"docker run -i --rm --entrypoint python {utils_image}"
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        out, _ = p.communicate(input=SCRIPT.encode())
        output = out.decode()
        if p.returncode != 0:
            self._logger.error("Failed to dump %s template.py\n%s", utils_image, output)
            raise RuntimeError("Failed to dump %s template.py" % utils_image)
        lines = output.splitlines()
        result = {}
        for line in lines:
            key, value = line.split()
            result[key] = value
        return result

    def _diff_template_py(self, registry_utils_image_revision) -> Dict[str, VersionChange]:

        current_revision = execute("git rev-parse HEAD").strip()

        registry_utils = self._build_utils(registry_utils_image_revision)
        r1 = self._dump_template(registry_utils)
        self._logger.debug("Registry utils image template (%s)\n%s",
                           registry_utils_image_revision,
                           "\n".join([f"{key} {value}" for key, value in r1.items()]))

        current_utils = self._build_utils(current_revision)
        r2 = self._dump_template(current_utils)
        self._logger.debug("Current utils image template (%s)\n%s",
                           current_revision,
                           "\n".join([f"{key} {value}" for key, value in r1.items()]))

        result = {}

        for key, new_version in r2.items():
            network, image = key.split("/")
            if key in r1:
                old_version = r1[key]
                if old_version != new_version:
                    result[image] = VersionChange(network, old_version, new_version)
            else:
                result[image] = VersionChange(network, None, new_version)

        self._logger.debug("Image utils template.py diff result: %s", result)

        return result

    def _get_template_modified_images(self, registry_utils_image_revision) -> List[str]:
        diff = self._diff_template_py(registry_utils_image_revision)
        result = set()
        for key, value in diff.items():
            # TODO improve new_version parsing
            image_tag = value.new_version.replace("exchangeunion/", "")
            result.add(image_tag)
        return list(result)

    def _checkout_ref(self, ref) -> GitReference:
        try:
            execute(f"git fetch")
            remote_ref = ref.replace("refs/heads", "refs/remotes/origin")
            execute(f"git checkout --detach {remote_ref}")
            revision = execute("git rev-parse HEAD")
            commit_message = execute("git show --format='%s' --no-patch HEAD").strip()
            return GitReference(ref, revision, commit_message)
        except Exception as e:
            raise RuntimeError("Failed to checkout reference %s" % ref) from e

    def _checkout_revision(self, revision) -> None:
        try:
            execute(f"git checkout {revision}")
        except Exception as e:
            raise RuntimeError("Failed to checkout revision %s" % revision) from e

    def get_modified_images(self, ref) -> Tuple[GitReference, List[str]]:
        with workspace(self.repo_dir):
            git_ref = self._checkout_ref(ref)

            images = os.listdir("images")

            latest_images = []
            version_images = []
            for image in images:
                self._logger.debug("Check %s", image)

                branch = ref.replace("refs/heads/", "")
                if branch == "master":
                    docker_image = self.dockerhub_client.get_image(f"exchangeunion/{image}", "latest")
                else:
                    docker_image = self.dockerhub_client.get_image(f"exchangeunion/{image}", "latest__" + branch.replace("/", "-"))
                    if not docker_image:
                        docker_image = self.dockerhub_client.get_image(f"exchangeunion/{image}", "latest")

                if docker_image:
                    revision = docker_image.revision
                    if revision.endswith("-dirty"):
                        self._logger.debug("Image %s is dirty", image)
                        latest_images.append(f"{image}:latest")
                    else:
                        if self._diff_image_with_revision(image, revision):
                            latest_images.append(f"{image}:latest")
                        else:
                            self._logger.debug("Image %s is up-to-date", image)
                        if image == "utils":
                            version_images = self._get_template_modified_images(docker_image.revision)
                else:
                    self._logger.debug("Registry image not found")
                    latest_images.append(f"{image}:latest")

            result = latest_images + version_images

            if len(result) > 0:
                self._logger.debug("Images to build: %s", ", ".join(result))
            else:
                self._logger.debug("No images need to build")

            result = set(result)
            result = sorted(result)
            result = list(result)

            return git_ref, result
