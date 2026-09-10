#!/usr/bin/env python3
"""
Catalogue-free runner for the ``general`` pipeline config.

``swift-pipeline`` requires a halo catalogue (VELOCIraptor / SOAP) and loads it
unconditionally, even when no scaling-relation (auto-plotter) figures are being
produced. If you only have snapshots and the on-the-fly log files, that step is
a blocker.

This runner bypasses ``swift-pipeline`` entirely: it reads ``config.yml`` and
invokes each plotting script directly. Every script enabled in the ``general``
config uses only snapshot + log data, so no catalogue is needed. A placeholder
value is passed for each script's required ``-c`` argument (the scripts never
open it).

When you later produce a halo catalogue, drop the catalogue-based figures back
into ``config.yml`` (or just use the full ``swift-pipeline`` with a real ``-c``);
this runner will keep working for the catalogue-free subset regardless.

Usage
-----
Single run::

    python run_pipeline.py -i /path/to/run -s snapshot_0077.hdf5 \
        -o /path/to/output -n "My EAGLE run" -j 8

Compare several runs (repeat -i/-s and, optionally, -n; lengths must match)::

    python run_pipeline.py -i runA runB -s snap_A.hdf5 snap_B.hdf5 \
        -o out -n "A" "B"

The figures listed in config.yml are written to the output directory, along
with an ``index.html`` grouping them by section.
"""

import argparse
import html
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-i", "--input", nargs="+", required=True,
                   help="Input director(y/ies) holding the snapshot(s) and log files "
                        "(SFR.txt, statistics.txt, timesteps.txt).")
    p.add_argument("-s", "--snapshots", nargs="+", required=True,
                   help="Snapshot filename(s), without directory. Must match -i in length.")
    p.add_argument("-o", "--output", required=True, help="Output directory for figures + index.html.")
    p.add_argument("-n", "--run-names", nargs="*", default=None,
                   help="Legend name(s) for the run(s). Must match -i in length if given.")
    p.add_argument("-C", "--config", default=SCRIPT_DIR,
                   help=f"Config directory containing config.yml. Default: {SCRIPT_DIR}")
    p.add_argument("-j", "--num-of-cpus", type=int, default=1,
                   help="Number of scripts to run concurrently. Default: 1.")
    p.add_argument("--only", nargs="*", default=None,
                   help="Only run these script basenames (e.g. density_temperature.py). Default: all.")
    p.add_argument("--debug", action="store_true", help="Print each script's full stdout/stderr.")
    args = p.parse_args()

    n = len(args.input)
    if len(args.snapshots) != n:
        p.error(f"-i has {n} entries but -s has {len(args.snapshots)}; they must match.")
    if args.run_names is not None and len(args.run_names) != n:
        p.error(f"-i has {n} entries but -n has {len(args.run_names)}; they must match.")
    return args


def build_command(entry, args):
    """Assemble the argv for a single plotting script."""
    n = len(args.input)
    script_path = os.path.join(args.config, entry["filename"])
    cmd = [
        sys.executable, script_path,
        "-C", args.config,
        "-d", *args.input,             # scripts use -d/--input-directories
        "-s", *args.snapshots,
        "-c", *(["none"] * n),         # required but unused placeholder catalogue
        "-o", args.output,
    ]
    if args.run_names is not None:
        cmd += ["-n", *args.run_names]
    return cmd


def run_one(entry, args):
    cmd = build_command(entry, args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return entry, proc


def write_index(config, results, output):
    """Build a simple HTML index grouping the produced figures by section."""
    ok = {e["output_file"] for e, p in results if p.returncode == 0
          and os.path.exists(os.path.join(output, e["output_file"]))}
    sections = {}
    for entry in config["scripts"]:
        if entry["output_file"] in ok:
            sections.setdefault(entry.get("section", "Other"), []).append(entry)

    parts = ["<!doctype html><meta charset='utf-8'>",
             "<title>General pipeline figures</title>",
             "<style>body{font-family:sans-serif;max-width:1100px;margin:2em auto;padding:0 1em}"
             "h2{border-bottom:2px solid #ccc;margin-top:2em}figure{margin:1.5em 0}"
             "img{max-width:100%;border:1px solid #ddd}figcaption{color:#444;font-size:.9em}</style>",
             "<h1>General pipeline figures</h1>"]
    for section, entries in sections.items():
        parts.append(f"<h2>{html.escape(section)}</h2>")
        for e in entries:
            parts.append(
                f"<figure><img src='{html.escape(e['output_file'])}' alt=''>"
                f"<figcaption><b>{html.escape(e.get('title',''))}</b> — "
                f"{html.escape(e.get('caption',''))}</figcaption></figure>")
    with open(os.path.join(output, "index.html"), "w") as fh:
        fh.write("\n".join(parts))


def main():
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    with open(os.path.join(args.config, "config.yml")) as fh:
        config = yaml.safe_load(fh)

    entries = config["scripts"]
    if args.only:
        wanted = set(args.only)
        entries = [e for e in entries if os.path.basename(e["filename"]) in wanted]
        if not entries:
            sys.exit(f"No scripts in config.yml match --only {args.only}")

    print(f"Running {len(entries)} scripts with {args.num_of_cpus} worker(s)...\n")
    results, failures = [], []
    with ThreadPoolExecutor(max_workers=args.num_of_cpus) as ex:
        futures = {ex.submit(run_one, e, args): e for e in entries}
        for fut in as_completed(futures):
            entry, proc = fut.result()
            name = os.path.basename(entry["filename"])
            if proc.returncode == 0:
                print(f"  [ ok ] {name}")
            else:
                print(f"  [FAIL] {name}")
                failures.append((name, proc))
            if args.debug and (proc.stdout or proc.stderr):
                print(proc.stdout, proc.stderr, sep="\n")
            results.append((entry, proc))

    write_index(config, results, args.output)

    print(f"\nDone: {len(results) - len(failures)}/{len(results)} succeeded. "
          f"Figures + index.html in {args.output}")
    if failures:
        print("\nFailures (last lines of stderr):")
        for name, proc in failures:
            tail = "\n    ".join((proc.stderr or "").strip().splitlines()[-4:])
            print(f"  {name}:\n    {tail or '(no stderr)'}")
        print("\nTip: a failure usually means that field/log column is missing in your "
              "run. Remove that entry from config.yml, or re-run with --debug for detail.")
        sys.exit(1)


if __name__ == "__main__":
    main()
