"""CLI for mechanical checks before AI video delivery."""

import argparse
import json
import sys
from pathlib import Path

from qualitygate.checks import apply_filter_findings, inspect_metadata
from qualitygate.probe import ProbeError, optional_filters, probe
from qualitygate.profiles import get_profile
from qualitygate.report import summarize, write_json, write_markdown


def build_parser():
    parser = argparse.ArgumentParser(description="Check AI video renders before client delivery.")
    parser.add_argument("files", nargs="+", help="video files to inspect")
    parser.add_argument("--profile", choices=["vertical", "horizontal", "square", "custom"], default="horizontal")
    parser.add_argument("--width", type=int, help="required video width for custom profile")
    parser.add_argument("--height", type=int, help="required video height for custom profile")
    parser.add_argument("--no-audio", action="store_true", help="allow a silent file")
    parser.add_argument("--json", dest="json_path", help="write machine-readable report")
    parser.add_argument("--markdown", dest="markdown_path", help="write a Markdown report")
    parser.add_argument("--no-filters", action="store_true", help="skip optional ffmpeg black/freeze/loudness checks")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        profile = get_profile(args.profile, args.width, args.height, not args.no_audio)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    results = []
    for name in args.files:
        try:
            metadata = probe(name)
            findings = inspect_metadata(metadata, profile)
            if not args.no_filters:
                apply_filter_findings(findings, optional_filters(name, metadata))
            result = summarize(name, findings)
        except ProbeError as exc:
            result = {"file": str(name), "status": "error", "error": str(exc), "findings": []}
        results.append(result)
        print(f"{result['status'].upper():5} {name}")
        for finding in result.get("findings", []):
            if finding["level"] != "pass":
                print(f"  {finding['level'].upper():5} {finding['code']}: {finding['message']}")
        if result.get("error"):
            print(f"  ERROR {result['error']}")

    if args.json_path:
        write_json(results, args.json_path)
    if args.markdown_path:
        write_markdown(results, profile, args.markdown_path)

    if any(r["status"] == "error" for r in results):
        return 2
    if any(r["status"] == "fail" or (args.strict and r["status"] == "warn") for r in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
