"""
Single source of truth for every file path and number format used by the
collection app. Mirrors DistVRT_v5.m / DistVRT_Integration.m:

    <root>\\stim\\MTB_child.wav
    <root>\\stim\\Female_2\\<word>.wav
    <root>\\stim\\Distractors_RMSscaled\\<name>-peak_RMS.wav
    <data>\\<ID>\\Visit<N>\\DistVRT_v5_<ID>          (log, no extension)
    <data>\\<ID>\\Visit<N>\\<ID>_<SNR>_<DistCond>_<Run>_<Trial>.wav

The data directory is resolved by _resolve_data_dir().
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
    return [part for part in re.split(r"[\\/]+", rel) if part]


_root = cfg("paths", "root", "")
if _root:
    ROOT = os.path.normpath(_root)
elif os.path.isdir(os.path.join(APP_DIR, "stim")):
    ROOT = APP_DIR
else:
    ROOT = os.path.dirname(APP_DIR)

STIM_DIR = os.path.join(ROOT, "stim")
NOISE_FILE = os.path.join(STIM_DIR, "MTB_child.wav")
TALKER = "Female_2"
WORD_DIR = os.path.join(STIM_DIR, TALKER)
DIST_DIR = os.path.join(STIM_DIR, "Distractors_RMSscaled")


def _child(parent, name):
    """Case-insensitive child lookup (Windows ignores case)."""
    try:
        for entry in os.listdir(parent):
            if (
                entry.lower() == name.lower()
                and os.path.isdir(os.path.join(parent, entry))
            ):
                return os.path.join(parent, entry)
    except OSError:
        pass

    return None


def _resolve_data_dir():
    """Resolve the collection data folder using config.ini."""
    full_path = cfg("paths", "data_dir", "")
    if full_path:
        return os.path.normpath(full_path)

    setting = cfg("paths", "data_subdir", "auto")
    if setting.lower() != "auto":
        return os.path.join(ROOT, *_split(setting))

    data_folder = _child(ROOT, "data")
    if data_folder:
        nested = _child(data_folder, "DistVRT_v5")
        if nested:
            return nested

        try:
            for entry in os.listdir(data_folder):
                entry_path = os.path.join(data_folder, entry)
                if not os.path.isdir(entry_path):
                    continue

                if _child(entry_path, "Visit1"):
                    return data_folder

                if any(
                    name.lower().startswith("visit")
                    for name in os.listdir(entry_path)
                    if os.path.isdir(os.path.join(entry_path, name))
                ):
                    return data_folder
        except OSError:
            pass

        return os.path.join(data_folder, "DistVRT_v5")

    return os.path.join(ROOT, "data", "DistVRT_v5")


DATA_DIR = _resolve_data_dir()

# Separate workbook used to queue completed runs for scoring.
SCORING_LOG_FILE = cfg(
    "paths",
    "scoring_log_file",
    r"\\bl-sphs-sphs\GustafsonLab\Projects\DistVRT_v5\DistVRT_v5_DataScoringLog.xlsx",
)

LISTS_DIR = APP_DIR
WORD_LIST_MAT = os.path.join(LISTS_DIR, "BalancedWordLists_cell.mat")
DIST_LIST_MAT = os.path.join(LISTS_DIR, "NarrowDistractList_cell.mat")
ASSETS_DIR = os.path.join(APP_DIR, "assets")
LOGS_DIR = os.path.join(APP_DIR, "logs")

LOG_PREFIX = "DistVRT_v5"

# First line of the log file, byte-for-byte as DistVRT_v5.m (ComputeAndReport) writes it.
HEADER = (
    "ObsName, TimeStamp, VisitNum,WordLevel, NoiseCond, SNR, DistCond, DistLevel, "
    "DistTime, RunNum, TrialNum, StimTalker, ListNum, StimWord, DistPresent, "
    "DistItem, TargetSide, Response, "
)


def matlab_num2str(value):
    """Reproduce MATLAB num2str for a scalar."""
    value = float(value)

    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == int(value):
        return str(int(value))

    digits = max(int(math.floor(math.log10(abs(value)))) + 5, 5)
    return (("%." + str(digits) + "g") % value)


def subject_dir(subject_id):
    return os.path.join(DATA_DIR, str(subject_id))


def visit_dir(subject_id, visit):
    return os.path.join(subject_dir(subject_id), "Visit%s" % visit)


def log_file(subject_id, visit):
    return os.path.join(
        visit_dir(subject_id, visit),
        "%s_%s" % (LOG_PREFIX, subject_id),
    )


def extras_dir(subject_id):
    # Kept outside Visit<N>.
    return os.path.join(subject_dir(subject_id), "Extras")


def questionnaire_dir():
    """Return the questionnaire folder inside the configured data folder."""
    return os.path.join(DATA_DIR, "Questionnaires")


def wav_name(subject_id, snr, dist_cond, run, trial):
    return "%s_%s_%s_%s_%s.wav" % (
        subject_id,
        matlab_num2str(snr),
        int(dist_cond),
        int(run),
        int(trial),
    )
