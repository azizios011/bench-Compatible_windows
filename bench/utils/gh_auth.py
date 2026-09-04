# imports - standard imports
import atexit
import os
import stat
import tempfile

# imports - third party imports
import click

TOKEN_ENV_VAR = "BENCH_GH_TOKEN"
ASKPASS_ENV_VAR = "GIT_ASKPASS"

# bench subcommands that make git go over the network and therefore require
# a fresh, verified GitHub Fine-Grained PAT. One prompt per bench command
# invocation, regardless of how many apps that command touches internally.
GIT_TOUCHING_COMMANDS = {"init", "get", "get-app", "update"}

_askpass_script_path = None


def _validate_token(token: str) -> str:
	"""Hits the GitHub API to confirm the PAT is live and returns the authenticated login."""
	import requests

	try:
		resp = requests.get(
			"https://api.github.com/user",
			headers={
				"Authorization": f"Bearer {token}",
				"Accept": "application/vnd.github+json",
				"X-GitHub-Api-Version": "2022-11-28",
			},
			timeout=10,
		)
	except requests.RequestException as e:
		raise click.ClickException(f"Could not reach GitHub API to verify token: {e}")

	if resp.status_code != 200:
		raise click.ClickException(
			f"GitHub token rejected (HTTP {resp.status_code}). Check that the fine-grained "
			"PAT is valid, unexpired, and scoped to the repos you're about to touch."
		)

	return resp.json().get("login", "unknown")


def _write_askpass_script() -> str:
	"""
	Writes a throwaway helper git can call for credentials. It reads the token from
	the environment at call time, so the token itself is never written to disk.
	"""
	fd, path = tempfile.mkstemp(prefix="bench-askpass-", suffix=".py")
	with os.fdopen(fd, "w") as f:
		f.write(
			"#!/usr/bin/env python3\n"
			"import os, sys\n"
			f"token = os.environ.get({TOKEN_ENV_VAR!r}, '')\n"
			"prompt = sys.argv[1] if len(sys.argv) > 1 else ''\n"
			"print('x-access-token' if 'Username' in prompt else token)\n"
		)
	os.chmod(path, stat.S_IRWXU)  # 0700, owner-only
	return path


def _cleanup_askpass_script():
	global _askpass_script_path
	if _askpass_script_path and os.path.exists(_askpass_script_path):
		try:
			os.remove(_askpass_script_path)
		except OSError:
			pass
	_askpass_script_path = None


def ensure_github_token(command: str):
	"""
	Gate for git-touching bench commands. Prompts for (and live-validates) a
	scoped GitHub Fine-Grained PAT before the command is allowed to proceed,
	then wires up an ephemeral GIT_ASKPASS helper so every git clone/pull/fetch
	spawned during this command authenticates with it.
	"""
	global _askpass_script_path

	if command not in GIT_TOUCHING_COMMANDS:
		return

	token = os.environ.get(TOKEN_ENV_VAR)
	if not token:
		click.secho(
			f"This bench requires a scoped GitHub Fine-Grained PAT to run `bench {command}`.",
			fg="yellow",
		)
		token = click.prompt("GitHub Personal Access Token", hide_input=True)

	username = _validate_token(token)
	click.secho(f"GitHub token verified for @{username}.", fg="green")

	os.environ[TOKEN_ENV_VAR] = token
	os.environ["GIT_TERMINAL_PROMPT"] = "0"

	_askpass_script_path = _write_askpass_script()
	os.environ[ASKPASS_ENV_VAR] = _askpass_script_path
	atexit.register(_cleanup_askpass_script)
