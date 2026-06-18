from __future__ import annotations

from dataclasses import dataclass


MAX_STREAM_CHARS = 12000
HEAD_CHARS = 6000
TAIL_CHARS = 4000


@dataclass(frozen=True)
class CommandOutput:
    exit_code: int
    stdout: str
    stderr: str
    elapsed_ms: int
    truncated: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "elapsed_ms": self.elapsed_ms,
            "truncated": self.truncated,
        }


def truncate_text(
    text: str,
    *,
    max_chars: int = MAX_STREAM_CHARS,
    head_chars: int = HEAD_CHARS,
    tail_chars: int = TAIL_CHARS,
) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False

    omitted = len(text) - head_chars - tail_chars
    marker = f"\n... output truncated, {omitted} characters omitted ...\n"
    return f"{text[:head_chars]}{marker}{text[-tail_chars:]}", True


def build_command_output(
    *,
    exit_code: int,
    stdout: str,
    stderr: str,
    elapsed_ms: int,
) -> CommandOutput:
    stdout, stdout_truncated = truncate_text(stdout)
    stderr, stderr_truncated = truncate_text(stderr)
    return CommandOutput(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        elapsed_ms=elapsed_ms,
        truncated=stdout_truncated or stderr_truncated,
    )
