from __future__ import annotations

import os
import re
from subprocess import check_output, PIPE, CalledProcessError
from typing import TYPE_CHECKING

from aiohttp import web
from requests import get
from .abc import Hook

if TYPE_CHECKING:
    pass


class GithubHook(Hook):
    def find_all_branches_in_xud_docker(self, repo, branch):
        # TODO get all branches which are affected by the changes of <branch> in <repo>
        wd = os.getcwd()
        try:
            bot_home = os.path.expanduser("~/.bot")
            if not os.path.exists(bot_home):
                os.mkdir(bot_home)
            os.chdir(bot_home)

            if not os.path.exists("xud-docker"):
                if os.system("git clone https://github.com/ExchangeUnion/xud-docker.git") != 0:
                    raise RuntimeError("Failed to clone xud-docker repository")

            os.chdir("xud-docker")

            if os.system("git fetch") != 0:
                raise RuntimeError("Failed to fetch updates for xud-docker")

            if os.system("git remote prune origin") != 0:
                raise RuntimeError("Failed to prune origin")

            try:
                output = check_output("git branch -r", shell=True, stderr=PIPE)
                branches = []
                for line in output.decode().splitlines():
                    line = line.strip()
                    line = line.replace("origin/HEAD -> ", "")
                    if line.startswith("origin/"):
                        line = line.replace("origin/", "")
                        branches.append(line)
            except Exception as e:
                raise RuntimeError(e, "Failed to get xud-docker branches")

            print("Remote branches:", branches)

            if os.system("git pull origin master") != 0:
                raise RuntimeError("Failed to update master")

            if repo == "ExchangeUnion/xud":
                result = []
                for b in branches:
                    print("Test branch:", b, branch)
                    try:
                        if b != "master":
                            os.system(f"git branch -D {b}")
                            os.system(f"git checkout {b}")
                        try:
                            output = check_output("cat images/xud/latest/Dockerfile | grep BRANCH=", shell=True,
                                                  stderr=PIPE)
                            p = re.compile("^ARG BRANCH=(.+)$")
                            m = p.match(output.decode())
                            if m:
                                dockerfile_branch = m.group(1)
                            else:
                                raise RuntimeError("Failed to get xud:latest BRANCH in {}".format(b))
                            if branch == dockerfile_branch:
                                result.append(b)
                        except CalledProcessError:
                            print("Failed to grep BRANCH from images/xud/latest/Dockerfile in " + b)
                    finally:
                        if os.system("git checkout master") != 0:
                            raise RuntimeError("Failed to checkout master")
                return result
        finally:
            os.chdir(wd)
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

    async def handle_upstream_repo_update(self, repo, branch, message):
        if repo == "ExchangeUnion/xud":
            branches = self.find_all_branches_in_xud_docker(repo, branch)
            # branches = filter_merged_branches(branches)
            if len(branches) == 0:
                branch_list = "nothing"
            else:
                branch_list = ", ".join(branches)
            lines = message.splitlines()
            first_line = lines[0]
            msg = "ExchangeUnion/xud branch **{}** was pushed ({}). Will trigger builds for {}."\
                .format(branch, first_line, branch_list)
            self.logger.debug(msg)
            self.context.discord_template.publish_message(msg)
            for b in branches:
                travis_msg = "%s(%s): %s" % (repo, branch, message)
                self.context.travis_client.trigger_travis_build(b, travis_msg)
        elif repo == "ExchangeUnion/market-maker-tools":
            branches = self.find_all_branches_in_xud_docker(repo, branch)
            # branches = filter_merged_branches(branches)
            if len(branches) == 0:
                branch_list = "nothing"
            else:
                branch_list = ", ".join(branches)
            lines = message.splitlines()
            first_line = lines[0]
            msg = "ExchangeUnion/market-maker-tools branch **{}** was pushed ({}). Will trigger builds for {}." \
                .format(branch, first_line, branch_list)
            self.logger.debug(msg)
            self.context.discord_template.publish_message(msg)
            for b in branches:
                travis_msg = "%s(%s): %s" % (repo, branch, message)
                self.context.travis_client.trigger_travis_build(b, travis_msg)

    async def handle(self, request: web.Request) -> web.Response:
        j = await request.json()
        try:
            repo = j["repository"]["full_name"]
            if repo == "ExchangeUnion/xud":
                ref = j["ref"]
                branch = ref.replace("refs/heads/", "")
                msg = j["head_commit"]["message"]
                self.logger.debug("github push %s %s: %s", repo, branch, msg)
                await self.handle_upstream_repo_update(repo, branch, msg)
            if repo == "ExchangeUnion/market-maker-tools":
                ref = j["ref"]
                branch = ref.replace("refs/heads/", "")
                msg = j["head_commit"]["message"]
                self.logger.debug("github push %s %s: %s", repo, branch, msg)
                await self.handle_upstream_repo_update(repo, branch, msg)
            else:
                self.logger.debug("Ignore GitHub %s webhook", repo)
        except Exception as e:
            raise RuntimeError(e, "Failed to parse github webhook: {}".format(j))
        return web.Response()
