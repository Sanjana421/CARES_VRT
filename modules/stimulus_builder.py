import os

import numpy as np
import soundfile as sf
from scipy.io import loadmat
from scipy.signal import resample as scipy_resample

from modules.calibration import scale_to_system_calibration

TARGET_FS = 44100


class StimulusBuilder:
    def __init__(self, base_path):
        self.base_path = base_path
        self.word_lists = self._load_word_lists()
        self.distractor_list = self._load_distractor_list()

    def _load_word_lists(self):
        mat = loadmat(os.path.join(self.base_path, "BalancedWordLists_cell.mat"))
        return mat["BalancedWordLists_cell"]

    def _load_distractor_list(self):
        mat = loadmat(os.path.join(self.base_path, "NarrowDistractList_cell.mat"))
        return mat["NarrowDistractList_cell"]

    def _extract_string(self, cell_entry):
        while isinstance(cell_entry, np.ndarray):
            cell_entry = cell_entry[0]
        return str(cell_entry)

    def _read_mono(self, path):
        audio, fs = sf.read(path)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        return audio.astype(np.float32), fs

    def _resample_to_target(self, audio, fs):
        if fs == TARGET_FS:
            return audio.astype(np.float32)
        new_len = int(round(len(audio) * TARGET_FS / fs))
        return scipy_resample(audio, new_len).astype(np.float32)

    def build_list(self, list_number, target_ear, target_spl_word, target_spl_dist, target_spl_noise=None):
        """
        Build 25 trials for one list.

        Word and distractor audio are calibrated here.
        target_spl_noise is accepted for API compatibility with main.py,
        but the continuous noise is handled separately by AudioEngine.
        """
        trials = []

        unpleasant = np.random.choice(np.arange(0, 15), 2, replace=False)
        neutral = np.random.choice(np.arange(15, 24), 2, replace=False)
        pleasant = np.random.choice(np.arange(24, 39), 2, replace=False)

        selected_indices = np.concatenate([unpleasant, neutral, pleasant])
        np.random.shuffle(selected_indices)

        selected_distractors = [
            self._extract_string(self.distractor_list[i])
            for i in selected_indices
        ]

        valid = False
        while not valid:
            rand_trials = np.sort(np.random.choice(np.arange(2, 25), 6, replace=False))
            if np.all(np.diff(rand_trials) > 1):
                valid = True

        distractor_map = dict(zip(rand_trials, selected_distractors))
        word_indices = np.random.permutation(25)

        for trial in range(25):
            word_idx = word_indices[trial]
            word = self._extract_string(self.word_lists[word_idx, list_number - 1])

            word_audio, word_fs = self._read_mono(
                os.path.join(self.base_path, "stim", "Female_2", f"{word}.wav")
            )
            word_audio = self._resample_to_target(word_audio, word_fs)
            word_audio = scale_to_system_calibration(word_audio, target_spl_word)

            delay_samples = int(0.5 * TARGET_FS)
            word_audio = np.concatenate((np.zeros(delay_samples, dtype=np.float32), word_audio))

            dist_present = 0
            dist_name = "none"
            dist_time = 99999

            if trial in distractor_map:
                dist_present = 1
                dist_name = distractor_map[trial]
                dist_filename = f"{dist_name}-peak_RMS.wav"

                dist_audio, dist_fs = self._read_mono(
                    os.path.join(self.base_path, "stim", "Distractors_RMSscaled", dist_filename)
                )
                dist_audio = self._resample_to_target(dist_audio, dist_fs)
                dist_audio = scale_to_system_calibration(dist_audio, target_spl_dist)

                max_jitter = int(0.75 * TARGET_FS)
                jitter = np.random.randint(1, max_jitter + 1)

                if jitter >= delay_samples:
                    dist_time = ((jitter / TARGET_FS) * 1000) - 500
                else:
                    dist_time = -((jitter / TARGET_FS) * 1000)

                dist_audio = np.concatenate((np.zeros(jitter, dtype=np.float32), dist_audio))

                if len(dist_audio) > len(word_audio):
                    word_audio = np.concatenate(
                        (word_audio, np.zeros(len(dist_audio) - len(word_audio), dtype=np.float32))
                    )
                else:
                    dist_audio = np.concatenate(
                        (dist_audio, np.zeros(len(word_audio) - len(dist_audio), dtype=np.float32))
                    )
            else:
                dist_audio = np.zeros_like(word_audio, dtype=np.float32)

            if target_ear == 2:
                stimulus = np.column_stack((dist_audio, word_audio))
            else:
                stimulus = np.column_stack((word_audio, dist_audio))

            trials.append({
                "stimulus": stimulus.astype(np.float32),
                "word": word,
                "dist_present": dist_present,
                "dist_name": dist_name,
                "dist_time": dist_time,
                "target_ear": target_ear,
            })

        return trials
