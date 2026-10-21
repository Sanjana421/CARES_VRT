"""
Checks collected data against the MATLAB DistVRT_v5 format that the scoring system reads.

    python tools\\check_data.py                 check everything under the data folder
    python tools\\check_data.py 2004            one participant
    python tools\\check_data.py --data-dir D:\\some\\folder

Per participant / Visit<N> it checks: log file name + header, 18 columns per row,
25 rows per condition, trial numbers 1-25, one TimeStamp per list, every row has its
wav (<ID>_<SNR>_<Dist>_<Run>_<Trial>.wav), no wav without a row, and the distractor
rules (6 trials from 3-25, never back to back; none when DistCond = 0).
"""
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules import paths                                    # noqa: E402
HEADER = paths.HEADER

COLS = [c.strip() for c in HEADER.split(",") if c.strip()]


def check_visit(subject, vdir, report):
    log = os.path.join(vdir, "%s_%s" % (paths.LOG_PREFIX, subject))
    tag = "%s\\%s" % (subject, os.path.basename(vdir))
    wavs = {f for f in os.listdir(vdir) if f.lower().endswith(".wav")}
    if not os.path.exists(log):
        report("FAIL", tag, "log file %s_%s not found (no extension expected)" % (paths.LOG_PREFIX, subject))
        if wavs:
            report("WARN", tag, "%d wav files but no log" % len(wavs))
        return
    with open(log, encoding="utf-8", errors="replace", newline="") as f:
        text = f.read()
    if "\r" in text:
        report("WARN", tag, "log has Windows line endings (MATLAB writes plain LF)")
    lines = text.split("\n")
    lines = [l.rstrip("\r") for l in lines if l.strip()]
    if [c.strip() for c in lines[0].split(",") if c.strip()] != COLS:
        report("FAIL", tag, "header differs from MATLAB header")
    groups = defaultdict(list)
    for n, line in enumerate(lines[1:], start=2):
        p = [x.strip() for x in line.split(",")]
        if len(p) != len(COLS):
            report("FAIL", tag, "line %d has %d columns, expected %d" % (n, len(p), len(COLS)))
            continue
        r = dict(zip(COLS, p))
        groups[(r["SNR"], r["DistCond"], r["RunNum"], r["ListNum"], r["TimeStamp"])].append(r)

    used = set()
    seen_cond = defaultdict(int)
    for (snr, dist, run, lst, ts), rows in sorted(groups.items()):
        cond = "SNR %s dist %s run %s list %s" % (snr, dist, run, lst)
        seen_cond[(snr, dist, run, lst)] += 1
        trials = sorted(int(r["TrialNum"]) for r in rows)
        if trials != list(range(1, 26)):
            report("FAIL", tag, "%s: trials are %s (expected 1-25 once each)" % (cond, trials))
        dp = [int(r["TrialNum"]) for r in rows if r["DistPresent"] == "1"]
        if dist == "1":
            if len(dp) != 6 or min(dp or [0]) < 3:
                report("FAIL", tag, "%s: distractor trials %s (expected 6 trials, all from 3-25)" % (cond, sorted(dp)))
            elif any(b - a < 2 for a, b in zip(sorted(dp), sorted(dp)[1:])):
                report("WARN", tag, "%s: back-to-back distractor trials %s (older MATLAB versions allowed this; "
                                    "the current DistVRT_v5.m does not)" % (cond, sorted(dp)))
            if any(r["DistTime"] == "99999" for r in rows if r["DistPresent"] == "1"):
                report("FAIL", tag, "%s: distractor trial with DistTime 99999" % cond)
        elif dp:
            report("FAIL", tag, "%s: DistCond 0 but DistPresent=1 on %s" % (cond, dp))
        for r in rows:
            w = "%s_%s_%s_%s_%s.wav" % (subject, snr, dist, run, r["TrialNum"])
            used.add(w)
            if w not in wavs:
                report("FAIL", tag, "%s: missing recording %s" % (cond, w))
    for k, c in seen_cond.items():
        if c > 1:
            report("WARN", tag, "SNR %s dist %s run %s list %s is in the log %d times" % (k + (c,)))
    extra = sorted(wavs - used)
    if extra:
        report("WARN", tag, "%d wav(s) not in the log, e.g. %s" % (len(extra), extra[:3]))
    return len(groups), len(lines) - 1, len(wavs)


def main():
    args = sys.argv[1:]
    data_dir = paths.DATA_DIR
    only = None
    i = 0
    while i < len(args):
        if args[i] == "--data-dir":
            data_dir = args[i + 1]
            i += 2
        else:
            only = args[i]
            i += 1
    if not os.path.isdir(data_dir):
        print("Data folder not found:", data_dir)
        return 1
    print("\n=== Data check: %s ===\n" % data_dir)
    counts = {"FAIL": 0, "WARN": 0}

    def report(level, tag, msg):
        counts[level] += 1
        print("[%-4s] %s: %s" % (level, tag, msg))

    total = 0
    for subject in sorted(os.listdir(data_dir)):
        sdir = os.path.join(data_dir, subject)
        if not os.path.isdir(sdir) or (only and subject != only) or subject.startswith(("_", ".")) or subject.lower() == "questionnaires":
            continue
        for v in sorted(os.listdir(sdir)):
            if re.match(r"^Visit\d+$", v) and os.path.isdir(os.path.join(sdir, v)):
                res = check_visit(subject, os.path.join(sdir, v), report)
                if res:
                    total += 1
                    print("       %s\\%s: %d list(s), %d log rows, %d recordings" % (subject, v, *res))
    print("\n%d visit folder(s) checked: %d problem(s), %d warning(s)." % (total, counts["FAIL"], counts["WARN"]))
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
