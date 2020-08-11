from subprocess import check_output, STDOUT, CalledProcessError
import logging

logger = logging.getLogger(__name__)


def execute(cmd: str) -> str:
    try:
        output = check_output(cmd, shell=True, stderr=STDOUT)
        return output.decode()
    except CalledProcessError as e:
        logger.debug("Failed to execute command (exit code %d)\n$ %s\n%s", e.returncode, e.cmd, e.output.decode().strip())
        raise e
