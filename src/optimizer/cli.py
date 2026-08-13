"""
Command-line interface for the Token Optimizer.

Examples
--------
    # Optimize a file and print the report
    token-optimizer prompt.txt

    # Aggressive mode, and save the shortened text to a file
    token-optimizer prompt.txt --aggressive --output short.txt

    # Pipe text in from another command
    echo "Please kindly summarize this, thank you so much." | token-optimizer

    # Just measure, don't reduce
    token-optimizer prompt.txt --measure-only

    # Show structural (caching) advice too
    token-optimizer prompt.txt --advise
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, pricing
from .advisor import advise
from .counter import measure
from .engine import optimize


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="token-optimizer",
        description="Measure and reduce the number of tokens in LLM prompts.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to a text file. If omitted, text is read from standard input.",
    )
    parser.add_argument(
        "-m", "--model",
        default=pricing.DEFAULT_MODEL,
        choices=sorted(pricing.PRICE_PER_MILLION_TOKENS),
        help=f"Model used for cost estimates (default: {pricing.DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "-a", "--aggressive",
        action="store_true",
        help="Also apply opt-in shorthand reducers (can change meaning).",
    )
    parser.add_argument(
        "-c", "--caveman",
        action="store_true",
        help="Caveman mode: drop articles (a/an/the) but keep readable sentences.",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Also compress with a local gpt4all model (free/offline; downloads once).",
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help="gpt4all model file to use for --llm (default: small Llama-3.2-1B).",
    )
    parser.add_argument(
        "--measure-only",
        action="store_true",
        help="Only count tokens / cost; do not reduce.",
    )
    parser.add_argument(
        "--advise",
        action="store_true",
        help="Also show structural suggestions (e.g. repeated blocks).",
    )
    parser.add_argument(
        "-o", "--output",
        help="Write the optimized text to this file instead of stdout.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _read_input(path: str | None) -> str:
    """Read text from a file, or from stdin when no path is given."""
    if path:
        try:
            # "utf-8-sig" transparently strips a leading BOM that Windows tools
            # (Notepad, PowerShell) often add — otherwise it corrupts the first
            # word and breaks duplicate detection.
            with open(path, "r", encoding="utf-8-sig") as handle:
                return handle.read()
        except FileNotFoundError:
            print(f"Error: file not found: {path}", file=sys.stderr)
            raise SystemExit(2)
    # No file argument — read whatever was piped in.
    if sys.stdin.isatty():
        print("Error: no input. Provide a file or pipe text in.", file=sys.stderr)
        raise SystemExit(2)
    return sys.stdin.read()


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code (0 = success)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    text = _read_input(args.file)

    if not text.strip():
        print("Error: input is empty.", file=sys.stderr)
        return 2

    # --- Measure-only mode -------------------------------------------------
    if args.measure_only:
        print(measure(text, model=args.model).summary())
        return 0

    # --- Optimize ----------------------------------------------------------
    result = optimize(
        text, model=args.model, aggressive=args.aggressive, caveman=args.caveman
    )

    final_text = result.optimized_text

    # Optional local-LLM pass on top of the rule-based result.
    if args.llm:
        from .counter import count_tokens
        from .local_llm import DEFAULT_LLM_MODEL, LocalLLMError, llm_compress

        model_name = args.llm_model or DEFAULT_LLM_MODEL
        print(f"[--llm] running local model {model_name} "
              f"(first run downloads it)…", file=sys.stderr)
        try:
            compressed = llm_compress(final_text, model=model_name)
        except LocalLLMError as exc:
            print(f"\n[--llm skipped] {exc}", file=sys.stderr)
        else:
            # Only accept the LLM version if it actually saved tokens.
            if count_tokens(compressed) < count_tokens(final_text):
                final_text = compressed
                print("[--llm] applied local model compression.", file=sys.stderr)
            else:
                print("[--llm] model output wasn't smaller; kept rule-based result.",
                      file=sys.stderr)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(final_text)
        print(f"Optimized text written to {args.output}\n", file=sys.stderr)
    else:
        # Print the report to stderr and the actual text to stdout, so the text
        # can be piped onward cleanly (e.g. `token-optimizer p.txt > short.txt`).
        print(final_text)

    print(result.summary(), file=sys.stderr)

    # --- Optional structural advice ---------------------------------------
    if args.advise:
        suggestions = advise(text)
        print("\nStructural suggestions:", file=sys.stderr)
        if not suggestions:
            print("  (none found)", file=sys.stderr)
        for suggestion in suggestions:
            print(f"  - {suggestion.message}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
