import logging
import os
import shutil
from collections import namedtuple
from contextlib import contextmanager
from subprocess import Popen, PIPE, STDOUT, check_output
from typing import List, Dict, Tuple, Union, Optional
import re

import git
from requests import get

from xud_docker_bot.docker import DockerHubClient, DockerImage
from xud_docker_bot.utils import execute

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


logger = logging.getLogger(__name__)


def ensure_repo(repo_dir: str, repo_url: str) -> git.Repo:
    try:
        repo = git.Repo(repo_dir)
    except git.NoSuchPathError:
        repo = git.Git(repo_dir).clone(repo_url)
    return repo


class Image:
    repos: Dict[str, git.Repo]

    def __init__(self, repos_dir, repo_url: Union[str, Dict[str, str]]):
        self.repos_dir = repos_dir
        if isinstance(repo_url, str):
            self.repos = {
                "default": self._setup_repo(repo_url)
            }
        else:
            self.repos = {key: self._setup_repo(value) for key, value in repo_url.items()}

    def _setup_repo(self, repo_url: str) -> git.Repo:
        repo_path = repo_url.replace("https://", "")
        repo_dir = os.path.join(self.repos_dir, repo_path)
        return ensure_repo(repo_dir, repo_url)

    def get_commit_message(self, commit: str, repo: str = "default") -> Optional[str]:
        try:
            return self.repos[repo].commit(commit).message
        except git.BadName:
            return None


class XudDockerRepo:
    def __init__(self, repos_dir: str, dockerhub: DockerHubClient):
        self.repos_dir = repos_dir
        self.dockerhub = dockerhub

        repo_dir = os.path.join(repos_dir, "xud-docker")
        repo_url = "https://github.com/ExchangeUnion/xud-docker.git"
        self.repo = ensure_repo(repo_dir, repo_url)

        self.images = {
            "xud": Image(self.repos_dir, "https://github.com/ExchangeUnion/xud"),
            "lndbtc": Image(self.repos_dir, "https://github.com/lightningnetwork/lnd"),
            "lndbtc-simnet": Image(self.repos_dir, "https://github.com/lightningnetwork/lnd"),
            "lndltc": Image(self.repos_dir, "https://github.com/ltcsuite/lnd"),
            "lndltc-simnet": Image(self.repos_dir, "https://github.com/ltcsuite/lnd"),
            "connext": Image(self.repos_dir, "https://github.com/connext/rest-api-client"),
            "bitcoind": Image(self.repos_dir, "https://github.com/bitcoin/bitcoin"),
            "litecoind": Image(self.repos_dir, "https://github.com/litecoin-project/litecoin"),
            "geth": Image(self.repos_dir, "https://github.com/ethereum/go-ethereum"),
            "arby": Image(self.repos_dir, "https://github.com/ExchangeUnion/market-maker-tools"),
            "boltz": Image(self.repos_dir, "https://github.com/BoltzExchange/boltz-lnd"),
            "webui": Image(self.repos_dir, {
                "frontend": "https://github.com/ExchangeUnion/xud-webui-poc",
                "backend": "https://github.com/ExchangeUnion/xud-socketio",
            }),
        }

    def get_affected_branches(self, image: str, branch: str) -> List[str]:
        """This function is invoked when xud-docker images (excluding utils) upstream repository got some updates.
        It is supposed to find out affected xud-docker branches which build the updated branch of that image.

        Current clumsy implementation just builds xud-docker master whenever an image upstream master branch changed.

        TODO find out **all** affected branches in xud-docker when **any** branches of upstream repository changed

        :param image: whose upstream repository got some updates (like new pushes or merged PRs)
        :param branch: the specific branch changed in the upstream repository
        :return:
        """
        # branches = filter_merged_branches(branches)
        if branch == "master":
            return ["master"]

        # return empty list by default
        return []

    def get_modified_images(self, ref: str) -> Tuple[GitReference, List[str]]:
        """Get modified images on specific branch

        :param ref: value is like "refs/heads/branch"
        :return:
        """
        p = re.compile(r"^refs/heads/(.+)$")
        m = p.match(ref)
        assert m, "Invalid ref: " + ref

        branch = m.group(1)

        # Fetch origin updates
        self.repo.remote("origin").fetch()

        # Checkout ref (detach)
        origin_ref = ref.replace("refs/heads", "refs/remotes/origin")
        self.repo.git.checkout("--detach", origin_ref)

        # Show current head
        logger.debug("Current head is %r", self.repo.head)
        head_commit = self.repo.head.commit
        git_ref = GitReference(ref, head_commit.commit_id, head_commit.message)

        history = self._get_branch_history(branch)

        images = os.listdir("images")

        latest_images = []
        version_images = []
        for image in images:
            self._checkout_origin_ref(ref)
            self._show_head()

            logger.debug("Check %s", image)

            docker_image = self._select_registry_image(branch, image, history)

            if docker_image:
                revision = docker_image.revision
                if revision.endswith("-dirty"):
                    logger.debug("Image %s is dirty", image)
                    latest_images.append(f"{image}:latest")
                else:
                    if self._diff_image_with_revision(image, revision):
                        latest_images.append(f"{image}:latest")
                    else:
                        logger.debug("Image %s is up-to-date (%s)", image, revision)
                    if image == "utils":
                        version_images = self._get_template_modified_images(docker_image)
            else:
                logger.debug("Registry image not found")
                latest_images.append(f"{image}:latest")

        result = latest_images + version_images

        if len(result) > 0:
            logger.debug("Images to build: %s", ", ".join(result))
        else:
            logger.debug("No images need to build")

        result = set(result)
        result = sorted(result)
        result = list(result)

        return git_ref, result

    def get_commit_message(self, commit: str) -> Optional[str]:
        """Get Git commit message of specific commit

        :param commit: Git commit hash
        :return: the Git commit message
        """
        try:
            return self.repo.commit(commit).message
        except git.BadName:
            return None

    def get_commit_message2(self, image: str, commit: str) -> str:
        """Get Git commit message for specific image

        :param image:
        :param commit:
        :return:
        """
        raise NotImplementedError

    def _clone_repo(self, repo_url, repo_dir):
        try:
            execute(f"git clone {repo_url} {repo_dir}")
        except Exception as e:
            raise RuntimeError("Failed to clone repository %s to folder %s" % (repo_url, repo_dir)) from e

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
            logger.debug("Image %s is different from %s\n%s", image, revision, "\n".join(lines))
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
        self._checkout_revision(revision)
        with workspace("images/utils/"):
            execute(f"docker build . -f {dockerfile} -t {tag}")
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
            logger.error("Failed to dump %s template.py\n%s", utils_image, output)
            raise RuntimeError("Failed to dump %s template.py" % utils_image)
        lines = output.splitlines()
        result = {}
        for line in lines:
            key, value = line.split()
            result[key] = value
        return result

    def _diff_template_py(self, registry_utils_image: DockerImage) -> Dict[str, VersionChange]:
        registry_revision = registry_utils_image.revision

        registry_utils = self._build_utils(registry_revision)
        r1 = self._dump_template(registry_utils)
        logger.debug("Registry utils:%s template\n%s",
                     registry_revision,
                     "\n".join([f"{key} {value}" for key, value in r1.items()]))

        current_revision = execute("git rev-parse HEAD").strip()
        current_utils = self._build_utils(current_revision)
        r2 = self._dump_template(current_utils)
        logger.debug("Current utils:%s template\n%s",
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

        logger.debug("Image utils template diff result: %s",
                     "\n".join([f"- {k}: {v}" for k, v in result.items()]))

        return result

    def _get_template_modified_images(self, registry_utils_image: DockerImage) -> List[str]:
        diff = self._diff_template_py(registry_utils_image)
        result = set()
        for key, value in diff.items():
            # TODO improve new_version parsing
            image_tag = value.new_version.replace("exchangeunion/", "")
            result.add(image_tag)
        return list(result)

    def _fetch_updates(self) -> None:
        output = execute(f"git fetch")
        logger.debug("Fetched xud-docker updates\n%s", output.strip())

    def _get_ref_details(self, ref) -> GitReference:
        revision = execute("git rev-parse HEAD")
        commit_message = execute("git show --format='%s' --no-patch HEAD").strip()
        return GitReference(ref, revision, commit_message)

    def _show_head(self) -> None:
        output = execute("git show --no-patch HEAD")
        logger.debug("Current HEAD of xud-docker repository\n%s", output.strip())

    def _checkout_origin_ref(self, ref) -> None:
        remote_ref = ref.replace("refs/heads", "refs/remotes/origin")
        execute(f"git checkout --detach {remote_ref}")

    def _checkout_revision(self, revision) -> None:
        try:
            execute(f"git checkout {revision}")
        except Exception as e:
            raise RuntimeError("Failed to checkout revision %s" % revision) from e

    def _get_branch_history(self, branch: str) -> List[str]:
        """Get the commit history of specific branch comparing to master

        :param branch:
        :return: a list of commit hashes
        """
        if branch == "master":
            # The commit 66f5d19 is the first commit that introduces utils image
            # Use this commit to shorten master history length
            output = self.repo.git.log("--pretty=format:%H", "66f5d19..")
        else:
            output = self.repo.git.log("--pretty=format:%H", "origin/master..")
        return output.splitlines()

    def _is_valid_branch_image(self, image: DockerImage, current_branch_history: List[str]) -> bool:
        if image.revision not in current_branch_history:
            return False
        return True

    def _select_registry_image(self, branch: str, image: str, current_branch_history: List[str]) -> DockerImage:
        """
        Select registry image (foo:tag or foo:tag__branch)
        """
        if branch == "master":
            tag = "latest"
            docker_image = self.dockerhub.get_image(f"exchangeunion/{image}", tag)
        else:
            tag = "latest__" + branch.replace("/", "-")
            docker_image = self.dockerhub.get_image(f"exchangeunion/{image}", tag)
            logger.debug("docker_image=%r", docker_image)
            logger.debug("current_branch_history=%r", current_branch_history)
            if not docker_image or not self._is_valid_branch_image(docker_image, current_branch_history):
                tag = "latest"
                docker_image = self.dockerhub.get_image(f"exchangeunion/{image}", tag)

        logger.debug("Selected registry image exchangeunion/%s:%s", image, tag)

        if not docker_image:
            raise RuntimeError("Image %s not found of branch %s" % (image, branch))

        return docker_image
