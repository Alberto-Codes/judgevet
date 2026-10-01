"""Give each pre-commit child a store owned by the test run, not the user.

Every ``pre-commit run`` writes its configuration path to ``db.db`` in the
store that ``PRE_COMMIT_HOME`` names. Without it, the store is the user-level
``~/.cache/pre-commit``, which every other process on the machine also
writes. SQLite there waits 5 seconds for a lock and then fails the test. See
issue #232. The pre-commit documentation describes ``PRE_COMMIT_HOME``:
https://github.com/pre-commit/pre-commit.com/blob/main/sections/advanced.md

One persistent seed store per machine holds the installed hook environments.
It costs about 18,000 inodes, mostly the Go toolchain for actionlint, so it
lives outside tmpfs ``/tmp`` and survives across runs.

- **Root.** ``$XDG_CACHE_HOME/judgevet-tests/pre-commit``, or
  ``~/.cache/judgevet-tests/pre-commit`` when ``XDG_CACHE_HOME`` is unset.
  ``JUDGEVET_TEST_PRE_COMMIT_SEED_ROOT`` overrides the root for CI or a
  scratch run.
- **Key.** The seed sits in ``<root>/<key>``. The key is a short sha256 over
  each repository URL and rev in ``.pre-commit-config.yaml``, the output of
  ``pre-commit --version``, and ``sys.executable``, because hook environments
  embed interpreter paths.
- **Marker.** The installer holds ``fcntl.flock`` on ``<root>.lock`` and
  writes ``ready`` inside the seed last. A seed without ``ready`` is removed
  and reinstalled under the lock.
- **Eviction.** Every run touches its seed's ``ready`` marker. After a
  successful install, still under the lock, the installer removes each other
  key directory whose marker is missing or older than 14 days. Another
  checkout's venv has its own key, so a seed used in the last 14 days stays.

Each test gets a home of its own under the run's temporary directory. The
home holds only copies of the seed's ``db.db`` and ``README``. That database
names the seed's repository directories by absolute path, so the hook
environments stay shared and download once per key.

Examples:
    ```python
    import os
    import subprocess

    env = os.environ | pre_commit_home_env()
    subprocess.run(["pre-commit", "run", "--all-files"], env=env, check=False)
    ```

See Also:
    - [tests.unit.test_configuration_gates][]: Runs the configured hooks.
    - [tests.unit.test_dependency_audit][]: Runs the pre-push audit hook.
"""

import fcntl
import functools
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".pre-commit-config.yaml"
RUN_VAR = "JUDGEVET_TEST_PRE_COMMIT_RUN"
ROOT_VAR = "JUDGEVET_TEST_PRE_COMMIT_SEED_ROOT"
READY = "ready"
STALE_SECONDS = 14 * 24 * 60 * 60
"""Age of an untouched ``ready`` marker after which a sibling seed is evicted."""


def _finish(process: subprocess.Popen[str], step: str) -> str:
    """Wait for one step, killing it if it outlives the timeout.

    Args:
        process: The running step, with stdout piped and stderr merged.
        step: The step name for the error message.

    Returns:
        The step's merged output.

    Raises:
        subprocess.TimeoutExpired: When the step runs past 600 seconds. The
            child is killed and reaped first, so no installer outlives the
            lock.
        RuntimeError: When the step exits non-zero.
    """
    try:
        output, _ = process.communicate(timeout=600)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise
    if process.returncode != 0:
        raise RuntimeError(f"{step} failed for the seed store:\n{output}")
    return output


@functools.cache
def seed_key() -> str:
    """Hash every input that a hook environment depends on.

    Returns:
        The first 16 hex digits of a sha256 over the configured repository
        URLs and revs, ``pre-commit --version`` and ``sys.executable``.
    """
    digest = hashlib.sha256()
    for repo in yaml.safe_load(CONFIG.read_text())["repos"]:
        digest.update(f"{repo['repo']}@{repo.get('rev', '')}\n".encode())
    # Popen, not subprocess.run: a test may patch run to record hook calls.
    probe = subprocess.Popen(
        [sys.executable, "-m", "pre_commit", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    version = _finish(probe, "pre-commit --version")
    digest.update(version.encode())
    digest.update(sys.executable.encode())
    return digest.hexdigest()[:16]


def seed_root() -> Path:
    """Locate the directory that holds one seed per key.

    Returns:
        ``JUDGEVET_TEST_PRE_COMMIT_SEED_ROOT`` when set, otherwise
        ``judgevet-tests/pre-commit`` under the user cache directory.
    """
    override = os.environ.get(ROOT_VAR)
    if override:
        return Path(override)
    cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(cache) / "judgevet-tests" / "pre-commit"


def _writable(function: Callable[[str], object], path: str, _: BaseException) -> None:
    """Make a read-only entry and its parent writable, then retry the removal.

    Go marks its module cache read-only, so a plain ``rmtree`` fails on it.

    Args:
        function: The ``os`` call that failed.
        path: The entry it failed on.
        _: The error ``rmtree`` caught.
    """
    os.chmod(os.path.dirname(path), stat.S_IRWXU)
    if not os.path.islink(path):
        os.chmod(path, stat.S_IRWXU)
    function(path)


def _remove(path: Path) -> None:
    """Remove a seed directory, read-only Go files included.

    Args:
        path: The directory to remove. A missing path is ignored.
    """
    if path.exists():
        shutil.rmtree(path, onexc=_writable)


def _install_seed(seed: Path) -> None:
    """Install every hook environment of the repository configuration.

    Popen stands in for ``subprocess.run`` because a test may patch ``run``
    to record its hook calls. The scratch repository is removed on exit.

    Args:
        seed: The empty store directory to install into.

    Raises:
        RuntimeError: When the repository init or ``pre-commit install-hooks`` exits
            non-zero.
        subprocess.TimeoutExpired: When either step runs past its timeout.
    """
    with tempfile.TemporaryDirectory(prefix="judgevet-seed-repo-") as scratch:
        shutil.copyfile(CONFIG, Path(scratch) / ".pre-commit-config.yaml")
        repo = subprocess.Popen(
            ["/usr/bin/git", "init", "-q"],
            cwd=scratch,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _finish(repo, "repository init")
        install = subprocess.Popen(
            [sys.executable, "-m", "pre_commit", "install-hooks"],
            cwd=scratch,
            env=os.environ | {"PRE_COMMIT_HOME": str(seed)},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _finish(install, "pre-commit install-hooks")


def seed_store() -> Path:
    """Return this key's seed store, installing it when it is not ready.

    Returns:
        The seed store directory, with every hook environment installed.
    """
    root = seed_root()
    seed = root / seed_key()
    marker = seed / READY
    if marker.is_file():
        marker.touch()
        return seed
    root.mkdir(parents=True, exist_ok=True)
    with open(root.with_name(root.name + ".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not marker.is_file():
            _remove(seed)
            _install_seed(seed)
            marker.touch()
            _evict_stale(root, seed)
    return seed


def _evict_stale(root: Path, seed: Path) -> None:
    """Remove sibling seeds that no run has touched for 14 days.

    The caller holds the root lock. A sibling without a ``ready`` marker is
    an abandoned install, because every install runs under the same lock.

    Args:
        root: The seed root holding one directory per key.
        seed: The seed just installed, which is kept.
    """
    cutoff = time.time() - STALE_SECONDS
    for sibling in root.iterdir():
        if not sibling.is_dir() or sibling == seed:
            continue
        sibling_marker = sibling / READY
        if not sibling_marker.is_file() or sibling_marker.stat().st_mtime < cutoff:
            _remove(sibling)


def pre_commit_home_env() -> dict[str, str]:
    """Name a fresh store for one pre-commit child, seeded from the seed.

    Merge the result into the child's env, never into ``os.environ``.

    Returns:
        ``{"PRE_COMMIT_HOME": <home>}`` for a new home under the run's
        temporary directory.

    Raises:
        RuntimeError: When the pytest session did not publish ``RUN_VAR``.
    """
    run = os.environ.get(RUN_VAR)
    if not run:
        raise RuntimeError(f"{RUN_VAR} is unset; tests/conftest.py publishes it")
    seed = seed_store()
    home = Path(tempfile.mkdtemp(prefix="pre-commit-home-", dir=run))
    for name in ("db.db", "README"):
        shutil.copyfile(seed / name, home / name)
    return {"PRE_COMMIT_HOME": str(home)}
