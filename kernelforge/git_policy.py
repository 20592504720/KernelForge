"""Process-local Git boundary. Repository configuration is untrusted input.

PATH, the OS trust store, proxy environment, SSH agent and user's SSH config
remain administrator/user trust boundaries. No safe.directory exception is added.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from .file_safety import read_regular_bytes


class GitPolicyError(ValueError):
    pass


_TRANSPORT_KEYS = frozenset({
    "http.proxy", "http.sslcainfo", "http.sslcapath", "http.sslbackend",
    "http.schannelusesslcainfo", "http.sslverify", "http.version",
})


def _config(path: Path, env: dict) -> list[tuple[str, str]]:
    try:
        data = read_regular_bytes(path, max_bytes=1024 * 1024)
    except (OSError, ValueError) as exc:
        raise GitPolicyError('linked, nonregular or oversized Git configuration refused') from exc
    # Parse exactly the bounded bytes inspected above; Git must not reopen a
    # pathname that could change between validation and parsing.
    result = subprocess.run(
        ["git", "config", "--file", "-", "--no-includes", "--null", "--list"],
        input=data, cwd=path.parent, env=env, capture_output=True, timeout=15, check=False)
    if result.returncode:
        raise GitPolicyError("Git configuration cannot be inspected safely")
    rows = []
    for record in result.stdout.split(b"\0"):
        if record:
            key, _, value = record.partition(b"\n")
            try:
                rows.append((key.decode("utf-8").lower(), value.decode("utf-8")))
            except UnicodeError:
                raise GitPolicyError('Git configuration must be valid UTF-8') from None
    return rows


def git_environment() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith("GIT_") and k.upper() not in ("SSH_ASKPASS", "GCM_INTERACTIVE")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0",
               GIT_TERMINAL_PROMPT="0", GIT_ATTR_NOSYSTEM="1")
    # Corporate proxy/CA settings can be supplied in an explicitly reviewed,
    # restricted file instead of silently inheriting executable Git settings.
    selected = os.environ.get("KERNELFORGE_GIT_TRANSPORT_CONFIG")
    settings = []
    if selected:
        path = Path(selected)
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise GitPolicyError("reviewed Git transport config must be an absolute regular file")
        settings = _config(path, env)
        for key, value in settings:
            if key not in _TRANSPORT_KEYS or (key == "http.sslverify" and value.lower() != "true"):
                raise GitPolicyError("unapproved Git transport configuration key/value")
    # Environment configuration takes precedence over repository configuration.
    settings += [("core.autocrlf", "false"), ("core.eol", "lf"),
                 ("core.hooksPath", os.devnull), ("core.fsmonitor", "false"),
                 ("http.sslVerify", "true"), ("http.followRedirects", "initial"),
                 ("credential.helper", ""), ("core.askPass", ""),
                 ("protocol.allow", "never"),
                 *[(f"protocol.{p}.allow", "always") for p in ("https", "http", "ssh", "git", "file")]]
    env["GIT_CONFIG_COUNT"] = str(len(settings))
    for i, (key, value) in enumerate(settings):
        env[f"GIT_CONFIG_KEY_{i}"] = key
        env[f"GIT_CONFIG_VALUE_{i}"] = value
    ssh = shutil.which("ssh")
    if ssh:
        env["GIT_SSH_COMMAND"] = "ssh -oBatchMode=yes -oStrictHostKeyChecking=yes"
    return env


def _pointer(path: Path, prefix: str = '') -> str:
    try:
        text = read_regular_bytes(path, max_bytes=16384).decode('utf-8').rstrip('\r\n')
    except (OSError, ValueError):
        raise GitPolicyError('unreadable Git directory pointer') from None
    if not text.startswith(prefix) or not text[len(prefix):] or any(ord(c) < 32 for c in text):
        raise GitPolicyError('invalid Git directory pointer')
    return text[len(prefix):]


def repository_layout(repo: Path) -> tuple[Path, Path, Path | None] | None:
    """Discover normal, bare, linked-worktree, submodule and separate-gitdir layouts.

    No Git process runs until local configuration has been inspected. Repository
    files and all parent directories must be controlled by the invoking user;
    this API is not a sandbox against a concurrent writer with the same rights.
    """
    repo = Path(repo).resolve(strict=True)
    for directory in (repo, *repo.parents):
        marker = directory / '.git'
        if os.path.lexists(marker):
            if marker.is_symlink() or getattr(marker.lstat(), 'st_file_attributes', 0) & 0x400:
                raise GitPolicyError('linked Git marker refused')
            gitdir = ((directory / _pointer(marker, 'gitdir: ')).resolve(strict=True)
                      if marker.is_file() else marker)
            worktree = directory
        elif (directory / 'HEAD').is_file() and (directory / 'objects').is_dir() and (directory / 'refs').is_dir():
            gitdir, worktree = directory, None
        else:
            continue
        common_pointer = gitdir / 'commondir'
        common = ((gitdir / _pointer(common_pointer)).resolve(strict=True)
                  if os.path.lexists(common_pointer) else gitdir)
        if not (gitdir / 'HEAD').is_file() or not (common / 'objects').is_dir():
            raise GitPolicyError('incomplete Git repository layout')
        return gitdir.resolve(), common.resolve(), worktree
    return None


_PASSIVE_CONFIG = re.compile(
    r'^(?:core\.(?:repositoryformatversion|filemode|bare|logallrefupdates|ignorecase|'
    r'precomposeunicode|symlinks|autocrlf|eol|longpaths|worktree)|'
    r'extensions\.(?:objectformat|worktreeconfig)|user\.(?:name|email)|'
    r'remote\..*\.(?:url|fetch|tagopt|promisor|partialclonefilter)|branch\..*\.(?:remote|merge)|'
    r'init\.defaultbranch)$', re.IGNORECASE)


def audit_repository(repo: Path, env: dict) -> tuple[Path, Path, Path | None] | None:
    """Fail closed for unreviewed local config, including bare repositories."""
    layout = repository_layout(repo)
    if layout is None:
        return None
    gitdir, common, worktree = layout
    for path in sorted({common / 'config', gitdir / 'config.worktree'}):
        if os.path.lexists(path):
            for key, value in _config(path, env):
                if not _PASSIVE_CONFIG.fullmatch(key):
                    # Subsection names can themselves contain secrets. Never log keys/values.
                    raise GitPolicyError('repository Git configuration requires review')
                if key == 'core.worktree':
                    candidate = gitdir / value
                    if worktree is None or worktree.resolve() != candidate.resolve():
                        raise GitPolicyError('Git core.worktree redirects outside the requested repository')
                if re.fullmatch(r'remote\..*\.url', key):
                    from .source import SourceError, validate_repository
                    try:
                        if not Path(value).is_absolute():
                            validate_repository(value)
                        elif any(ord(c) < 32 for c in value):
                            raise SourceError('invalid local source path')
                    except (SourceError, ValueError):
                        raise GitPolicyError('repository remote URL requires review') from None
    # Explicit --git-dir/--work-tree bypass Git's normal ownership check.
    # Require native repository discovery after the configuration audit and
    # before allowing any explicitly located command. Do not pass a repository
    # locator or add safe.directory exceptions to this probe.
    try:
        native = subprocess.run(
            ["git", "rev-parse", "--absolute-git-dir"],
            cwd=Path(repo).resolve(strict=True), env=env,
            capture_output=True, timeout=15, check=False,
        )
        if native.returncode:
            raise GitPolicyError('native Git repository discovery/ownership check failed')
        discovered = Path(native.stdout.decode('utf-8', errors='strict').rstrip('\r\n'))
        if not discovered.is_absolute() or discovered.resolve(strict=True) != gitdir:
            raise GitPolicyError('native Git discovery differs from audited repository')
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise GitPolicyError('native Git repository discovery could not be verified') from exc
    return layout


def git_command(args, *, cwd=None, env=None) -> list[str]:
    environment = env if env is not None else git_environment()
    if environment.get("GIT_CONFIG_NOSYSTEM") != "1" or environment.get("GIT_NO_REPLACE_OBJECTS") != "1":
        raise GitPolicyError("Git command requires the isolated process environment")
    count = environment.get("GIT_CONFIG_COUNT", "0")
    if not count.isdigit() or int(count) > 128 or any(f"GIT_CONFIG_KEY_{i}" not in environment or
                                  f"GIT_CONFIG_VALUE_{i}" not in environment
                                  for i in range(int(count))):
        raise GitPolicyError("incomplete isolated Git configuration")
    permitted_env = {"GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_NO_REPLACE_OBJECTS",
                     "GIT_OPTIONAL_LOCKS", "GIT_TERMINAL_PROMPT", "GIT_ATTR_NOSYSTEM",
                     "GIT_CONFIG_COUNT", "GIT_SSH_COMMAND", "GIT_SSH_VARIANT"}
    permitted_env.update(f"GIT_CONFIG_{kind}_{i}" for i in range(int(count))
                         for kind in ("KEY", "VALUE"))
    if any(key.startswith("GIT_") and key not in permitted_env for key in environment):
        raise GitPolicyError("unexpected Git process-control environment variable")
    settings = [(environment[f"GIT_CONFIG_KEY_{i}"].lower(), environment[f"GIT_CONFIG_VALUE_{i}"])
                for i in range(int(count))]
    allowed = _TRANSPORT_KEYS | {"core.autocrlf", "core.eol", "core.hookspath", "core.fsmonitor",
                                 "http.followredirects", "credential.helper", "core.askpass",
                                 "protocol.allow", *(f"protocol.{p}.allow" for p in
                                                       ("https", "http", "ssh", "git", "file"))}
    if any(key not in allowed for key, _ in settings):
        raise GitPolicyError("unexpected Git process configuration key")
    if (environment.get("GIT_CONFIG_GLOBAL") != os.devnull or
            environment.get("GIT_TERMINAL_PROMPT") != "0" or
            environment.get("GIT_NO_REPLACE_OBJECTS") != "1" or
            environment.get("GIT_OPTIONAL_LOCKS") != "0"):
        raise GitPolicyError("Git global configuration and terminal prompting must remain isolated")
    if environment.get("GIT_SSH_COMMAND") not in (None, "ssh -oBatchMode=yes -oStrictHostKeyChecking=yes"):
        raise GitPolicyError("SSH host verification or non-interactive mode was changed")
    if any(key == "http.sslverify" and value.lower() != "true" for key, value in settings):
        raise GitPolicyError("TLS verification cannot be disabled")
    if any(key == "http.followredirects" and value.lower() != "initial"
           for key, value in settings):
        raise GitPolicyError("Git redirect policy is not permitted")
    if any(key == "protocol.allow" and value.lower() != "never" for key, value in settings):
        raise GitPolicyError("Git protocol helper policy is not permitted")
    if any(key.startswith("protocol.") and key.endswith(".allow") and key != "protocol.allow"
           and value.lower() != "always" for key, value in settings):
        raise GitPolicyError("Git transport allow-list cannot be changed")
    required = {"core.autocrlf": "false", "core.eol": "lf", "core.hookspath": os.devnull,
                "core.fsmonitor": "false", "http.sslverify": "true",
                "http.followredirects": "initial", "credential.helper": "", "core.askpass": "",
                "protocol.allow": "never"}
    for key, value in required.items():
        if dict(settings).get(key) != value or any(k == key and v != value for k, v in settings):
            raise GitPolicyError("required Git process policy is missing or changed")
    repo = Path(cwd or Path.cwd())
    remaining = list(args)
    index = 0
    while index < len(remaining) and remaining[index].startswith('-'):
        argument = remaining[index]
        if argument in ('-C', '-c') and index + 1 < len(remaining):
            value = remaining[index + 1]
            if argument == '-C':
                repo = repo / value
            elif not re.fullmatch(r'core\.(?:autocrlf=(?:true|false|input)|eol=(?:lf|crlf|native))', value, re.IGNORECASE):
                raise GitPolicyError('unreviewed Git command configuration override')
            index += 2
        elif argument in ('--no-optional-locks', '--no-pager', '--literal-pathspecs'):
            index += 1
        else:
            raise GitPolicyError('unreviewed Git repository or process override')
    if index == len(remaining):
        raise GitPolicyError('Git subcommand is required')
    subcommand = remaining[index]
    # These commands establish or query a repository-independent endpoint.
    # Auditing the caller's current repository here would incorrectly inject
    # its --git-dir into `clone`/`init` and make the new destination ambiguous.
    if subcommand in {'clone', 'init', 'ls-remote', 'version', 'help'}:
        return ['git', *remaining]
    layout = audit_repository(repo, environment)
    # Pin discovery to exactly the layout inspected above. This also avoids a
    # different parent repository being selected after a directory is renamed.
    pinned = []
    if layout is not None:
        gitdir, _, worktree = layout
        pinned = ['--git-dir=' + str(gitdir)]
        if worktree is not None:
            pinned += ['--work-tree=' + str(worktree)]
    return ['git', *remaining[:index], *pinned, *remaining[index:]]
