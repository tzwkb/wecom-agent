"""Thin wrapper around WecomTeam wecom-cli."""

import json
import subprocess


class WecomCliError(RuntimeError):
    def __init__(self, argv, returncode, stdout, stderr):
        self.argv = list(argv)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        message = stderr.strip() or stdout.strip() or f"wecom-cli exited with {returncode}"
        super().__init__(message)


def run_json(args, payload=None, timeout=60, cli="wecom-cli", run=subprocess.run):
    argv = [cli] + list(args)
    if payload is not None:
        argv.extend(["--json", json.dumps(payload, ensure_ascii=False, separators=(",", ":"))])

    completed = run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    if completed.returncode != 0:
        raise WecomCliError(argv, completed.returncode, completed.stdout, completed.stderr)

    output = completed.stdout.strip()
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return output


def run_text(args, timeout=30, cli="wecom-cli", run=subprocess.run):
    argv = [cli] + list(args)
    completed = run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    if completed.returncode != 0:
        raise WecomCliError(argv, completed.returncode, completed.stdout, completed.stderr)
    return completed.stdout.strip()


def require_confirmation(confirmed, action):
    if not confirmed:
        raise PermissionError(f"{action} is an online write operation; pass confirmed=True after user approval.")


def target_payload(docid=None, url=None):
    if bool(docid) == bool(url):
        raise ValueError("Pass exactly one of docid or url.")
    return {"docid": docid} if docid else {"url": url}


def doc_call(command, payload=None, runner=None):
    call = runner or run_json
    return call(["doc", command], payload)


def auth_status(runner=None):
    call = runner or run_text
    return call(["auth", "show", "--auth-status"])


def version(runner=None):
    call = runner or run_text
    return call(["--version"])


def doc_command_supported(command, runner=None):
    call = runner or run_text
    try:
        call(["doc", command, "--schema"])
    except WecomCliError:
        return False
    return True

