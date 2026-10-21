"""
Builds the 25 stereo trials for one list.  Port of MakeStim in DistVRT_v5.m.
All files are read from the MATLAB experiment folder (see modules/paths.py).
"""
import os
from math import gcd

import numpy as np
import soundfile as sf
from scipy.io import loadmat
from scipy.signal import resample_poly

from modules import paths
from modules.calibration import scale_to_system_calibration

TARGET_FS = 44100          # MOTU rate used by MATLAB (FS_MOTU)
N_TRIALS = 25


def _cell_str(entry):
    while isinstance(entry, np.ndarray):
        entry = entry[0]
    return str(entry)


def _read_mono(path):
    audio, fs = sf.read(path)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio.astype(np.float64), fs


def _resample(audio, fs_in, fs_out=TARGET_FS):
    """Polyphase resampling, the same family of filter as MATLAB resample()."""
    if fs_in == fs_out:
        return audio
    g = gcd(int(fs_out), int(fs_in))
    return resample_poly(audio, int(fs_out) // g, int(fs_in) // g)


class StimulusBuilder:
    def __init__(self):
        self.word_lists = loadmat(paths.WORD_LIST_MAT)["BalancedWordLists_cell"]
        self.distractors = loadmat(paths.DIST_LIST_MAT)["NarrowDistractList_cell"]
        self.n_lists = self.word_lists.shape[1]

    def build_list(self, list_number, target_ear, dist_cond,
                   target_spl_word, target_spl_dist):
        if not 1 <= int(list_number) <= self.n_lists:
            raise ValueError("List number must be between 1 and %d" % self.n_lists)

        # --- choose 6 distractors: 2 unpleasant, 2 neutral, 2 pleasant (MATLAB randperm) ---
        picks = np.concatenate([
            np.random.choice(np.arange(0, 15), 2, replace=False),    # unpleasant 1-15
            np.random.choice(np.arange(15, 24), 2, replace=False),   # neutral   16-24
            np.random.choice(np.arange(24, 39), 2, replace=False),   # pleasant  25-39
        ])
        np.random.shuffle(picks)
        dist_names = [_cell_str(self.distractors[i]) for i in picks]

        # --- 6 trials out of 3..25, never back to back (randsample(3:25,6)) ---
        while True:
            dist_trials = np.sort(np.random.choice(np.arange(2, 25), 6, replace=False))
            if np.all(np.diff(dist_trials) > 1):
                break
        dist_map = {int(t): n for t, n in zip(dist_trials, dist_names)}

        word_order = np.random.permutation(N_TRIALS)
        delay = int(round(0.5 * TARGET_FS))            # word always starts 500 ms in
        trials = []

        for t in range(N_TRIALS):
            word = _cell_str(self.word_lists[word_order[t], int(list_number) - 1])
            audio, fs = _read_mono(os.path.join(paths.WORD_DIR, word + ".wav"))
            audio = scale_to_system_calibration(_resample(audio, fs), target_spl_word)
            word_audio = np.concatenate([np.zeros(delay, np.float32), audio])

            has_item = t in dist_map
            # MATLAB logs the distractor name on these 6 trials even when DistCond = 0
            # (DistPresent stays 0 and nothing is played) - kept so logs stay identical.
            dist_name = dist_map[t] if has_item else "none"
            dist_present = 1 if (has_item and int(dist_cond) == 1) else 0
            dist_time = 99999

            if dist_present:
                d, dfs = _read_mono(os.path.join(paths.DIST_DIR, dist_name + "-peak_RMS.wav"))
                d = scale_to_system_calibration(_resample(d, dfs), target_spl_dist)
                jit = int(np.random.randint(1, int(round(0.75 * TARGET_FS)) + 1))
                if jit >= delay:
                    dist_time = (jit / TARGET_FS) * 1000 - 500    # after word onset
                else:
                    dist_time = -((jit / TARGET_FS) * 1000)       # before word onset
                d = np.concatenate([np.zeros(jit, np.float32), d])
                n = max(len(d), len(word_audio))
                d = np.pad(d, (0, n - len(d)))
                word_audio = np.pad(word_audio, (0, n - len(word_audio)))
            else:
                d = np.zeros(len(word_audio), np.float32)

            if int(target_ear) == 2:
                stim = np.column_stack((d, word_audio))      # word right, distractor left
            else:
                stim = np.column_stack((word_audio, d))      # word left, distractor right

            trials.append({
                "stimulus": stim.astype(np.float32),
                "word": word,
                "dist_present": dist_present,
                "dist_name": dist_name,
                "dist_time": dist_time,
                "target_ear": int(target_ear),
            })
        return trials
