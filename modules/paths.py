"""
Single source of truth for every file path and number format used by the
collection app.  Mirrors DistVRT_v5.m / DistVRT_Integration.m exactly:

    <root>\\stim\\MTB_child.wav
    <root>\\stim\\Female_2\\<word>.wav
    <root>\\stim\\Distractors_RMSscaled\\<name>-peak_RMS.wav
    <data>\\<ID>\\Visit<N>\\DistVRT_v5_<ID>          (log, no extension)
    <data>\\<ID>\\Visit<N>\\<ID>_<SNR>_<DistCond>_<Run>_<Trial>.wav
where <data> is  <root>\\data\\DistVRT_v5  (MATLAB script) or  <root>\\Data  (the lab's
Data folder, where participants sit directly under Data) - see _resolve_data_dir().
"""
import configparser
import math
import os
import re

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(APP_DIR, "config.ini")

_cfg = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
_cfg.read(CONFIG_FILE, encoding="utf-8")


def cfg(section, key, default=""):
    return _cfg.get(section, key, fallback=default).strip()


def cfg_float(section, key, default):
    try:
        return float(cfg(section, key, str(default)))
    except ValueError:
        return float(default)


def cfg_int(section, key, default):
    return int(round(cfg_float(section, key, default)))


def _split(rel):
    return [p for p in re.split(r"[\\/]+", rel) if p]


_root = cfg("paths", "root", "")
if _root:
    ROOT = os.path.normpath(_root)
elif os.path.isdir(os.path.join(APP_DIR, "stim")):
    ROOT = APP_DIR                      # stim folder sits next to main.py (GitHub layout)
else:
    ROOT = os.path.dirname(APP_DIR)

STIM_DIR = os.path.join(ROOT, "stim")
NOISE_FILE = os.path.join(STIM_DIR, "MTB_child.wav")
TALKER = "Female_2"
WORD_DIR = os.path.join(STIM_DIR, TALKER)
DIST_DIR = os.path.join(STIM_DIR, "Distractors_RMSscaled")



def _child(parent, name):
    """Case-insensitive child lookup (Windows ignores case; keeps Linux tests honest)."""
    try:
        for d in os.listdir(parent):
            if d.lower() == name.lower() and os.path.isdir(os.path.join(parent, d)):
                return os.path.join(parent, d)
    except OSError:
        pass
    return None


def _resolve_data_dir():
    """data_subdir = auto (default):
         1. <root>\\data\\DistVRT_v5   if it exists          (literal MATLAB path)
         2. <root>\\Data                if participant folders (<ID>\\Visit<N>) sit directly
                                         in it                  (layout of the lab's Data folder)
         3. otherwise                    <root>\\data\\DistVRT_v5  (MATLAB path, created on use)
       Anything else in config.ini is taken as a path relative to root."""
    full = cfg("paths", "data_dir", "")
    if full:                                   # full path, e.g. the server data folder
        return os.path.normpath(full)
    setting = cfg("paths", "data_subdir", "auto")
    if setting.lower() != "auto":
        return os.path.join(ROOT, *_split(setting))
    data = _child(ROOT, "data")
    if data:
        nested = _child(data, "DistVRT_v5")
        if nested:
            return nested
        try:
            for d in os.listdir(data):
                if _child(os.path.join(data, d), "Visit1") or any(
                        x.lower().startswith("visit") for x in os.listdir(os.path.join(data, d))
                        if os.path.isdir(os.path.join(data, d, x))):
                    return data
        except OSError:
            pass
        return os.path.join(data, "DistVRT_v5")
    return os.path.join(ROOT, "data", "DistVRT_v5")


DATA_DIR = _resolve_data_dir()

LISTS_DIR = APP_DIR                      # the *_cell.mat files sit next to main.py
WORD_LIST_MAT = os.path.join(LISTS_DIR, "BalancedWordLists_cell.mat")
DIST_LIST_MAT = os.path.join(LISTS_DIR, "NarrowDistractList_cell.mat")
ASSETS_DIR = os.path.join(APP_DIR, "assets")
LOGS_DIR = os.path.join(APP_DIR, "logs")

LOG_PREFIX = "DistVRT_v5"

# First line of the log file, byte-for-byte as DistVRT_v5.m (ComputeAndReport) writes it.
HEADER = ("ObsName, TimeStamp, VisitNum,WordLevel, NoiseCond, SNR, DistCond, DistLevel, "
          "DistTime, RunNum, TrialNum, StimTalker, ListNum, StimWord, DistPresent, "
          "DistItem, TargetSide, Response, ")


def matlab_num2str(x):
    """Reproduce MATLAB num2str for a scalar (integers print without '.0')."""
    x = float(x)
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Inf" if x > 0 else "-Inf"
    if x == int(x):
        return str(int(x))
    digits = max(int(math.floor(math.log10(abs(x)))) + 5, 5)
    return ("%." + str(digits) + "g") % x


def subject_dir(subject_id):
    return os.path.join(DATA_DIR, str(subject_id))


def visit_dir(subject_id, visit):
    return os.path.join(subject_dir(subject_id), "Visit%s" % visit)


def log_file(subject_id, visit):
    return os.path.join(visit_dir(subject_id, visit), "%s_%s" % (LOG_PREFIX, subject_id))


def extras_dir(subject_id):
    # Kept OUTSIDE Visit<N> so the Visit folder holds only what MATLAB puts there.
    return os.path.join(subject_dir(subject_id), "Extras")


def questionnaire_dir():
    """One folder for all questionnaires, inside the data folder."""
    return os.path.join(DATA_DIR, "Questionnaires")


def wav_name(subject_id, snr, dist_cond, run, trial):
    return "%s_%s_%s_%s_%s.wav" % (
        subject_id, matlab_num2str(snr), int(dist_cond), int(run), int(trial))
