"""
Start-up self-check.  Used by main.py (silently) and Check_Setup.bat (full report).
Every path it tests is the one the experiment really uses.
"""
import os
import shutil
import sys

from modules import paths


def _ex(entry):
    import numpy as np
    while isinstance(entry, np.ndarray):
        entry = entry[0]
    return str(entry)


def run_checks(check_audio=True):
    out = []
    ok = lambda m: out.append(("OK", m))          # noqa: E731
    fail = lambda m: out.append(("FAIL", m))      # noqa: E731
    warn = lambda m: out.append(("WARN", m))      # noqa: E731

    ok("Python %s" % sys.version.split()[0])
    ok("Experiment folder (root): %s" % paths.ROOT)
    if not os.path.isdir(paths.ROOT):
        fail("Experiment folder not found: %s" % paths.ROOT)
        return out

    # --- stimulus files -------------------------------------------------
    for label, p in (("stim\\MTB_child.wav", paths.NOISE_FILE),
                     ("stim\\Female_2", paths.WORD_DIR),
                     ("stim\\Distractors_RMSscaled", paths.DIST_DIR)):
        (ok if os.path.exists(p) else fail)(
            ("Found " if os.path.exists(p) else "MISSING ") + label + "  (" + p + ")")

    # --- word / distractor lists vs. wav files --------------------------
    try:
        from scipy.io import loadmat
        words = loadmat(paths.WORD_LIST_MAT)["BalancedWordLists_cell"]
        dists = loadmat(paths.DIST_LIST_MAT)["NarrowDistractList_cell"]
        miss_w = sorted({_ex(words[r, c]) for r in range(words.shape[0])
                         for c in range(words.shape[1])
                         if not os.path.exists(os.path.join(paths.WORD_DIR, _ex(words[r, c]) + ".wav"))})
        miss_d = [_ex(dists[i]) for i in range(dists.shape[0])
                  if not os.path.exists(os.path.join(paths.DIST_DIR, _ex(dists[i]) + "-peak_RMS.wav"))]
        if miss_w or miss_d:
            fail("Missing stimulus files: words=%s distractors=%s" % (miss_w[:8], miss_d[:8]))
        else:
            ok("All %d words (%d lists) and %d distractors have wav files"
               % (words.shape[0] * words.shape[1], words.shape[1], dists.shape[0]))
    except Exception as exc:                                            # noqa: BLE001
        fail("Could not read word lists in lists\\ : %s" % exc)

    # --- data folder is writable ----------------------------------------
    try:
        os.makedirs(paths.DATA_DIR, exist_ok=True)
        probe = os.path.join(paths.DATA_DIR, "_write_test.tmp")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        ok("Data folder is writable: %s" % paths.DATA_DIR)
        ok("Layout: %s" % ("participants directly under Data\\" if os.path.basename(paths.DATA_DIR).lower() == "data" else "data\\DistVRT_v5\\<ID>\\Visit<N> (as in DistVRT_v5.m)"))
        free = shutil.disk_usage(paths.DATA_DIR).free / 1e9
        (ok if free > 2 else warn)("%.1f GB free on the data drive" % free)
    except OSError as exc:
        fail("Cannot write to data folder %s : %s" % (paths.DATA_DIR, exc))

    # --- calibration -----------------------------------------------------
    from modules import calibration as cal
    ok("Calibration (GitHub values): system %.1f dB SPL @ RMS %.1f" % (cal.SYSTEM_DB_SPL, cal.SYSTEM_CAL_RMS))

    # --- audio -----------------------------------------------------------
    if check_audio:
        try:
            from modules import audio_engine as ae
            i, o, host = ae.resolve_devices()
            import sounddevice as sd
            ok("MOTU input  #%d  %s" % (i, sd.query_devices(i)["name"]))
            ok("MOTU output #%d  %s   (driver: %s)" % (o, sd.query_devices(o)["name"], host))
            warn("Before collecting: Windows volume = 44 for 'Out 3-4', SLA4 knobs untouched "
                 "(see the calibration document).")
        except Exception as exc:                                        # noqa: BLE001
            fail(str(exc))
    return out


def main():
    want_tone = "--tone" in sys.argv
    print("\n=== DistVRT collection - setup check ===\n")
    results = run_checks(check_audio=True)
    for level, msg in results:
        print("[%-4s] %s" % (level, msg))
    bad = [m for lvl, m in results if lvl == "FAIL"]
    print("\n" + ("ALL GOOD - ready to collect data." if not bad
                  else "%d problem(s) found - fix the [FAIL] lines above." % len(bad)))
    if want_tone and not bad:
        from modules.audio_engine import AudioEngine
        print("\nPlaying a quiet tone: LEFT speaker first, then RIGHT ...")
        AudioEngine().play_test_tone()
        print("Done. You should have heard it from each speaker once.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
