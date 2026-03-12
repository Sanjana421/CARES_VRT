import os
import numpy as np
import soundfile as sf
from scipy.io import loadmat
from scipy.signal import resample

from modules.calibration import scale_to_system_calibration


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

    def _load_and_prepare_noise(self, target_spl_noise):
        noise_path = os.path.join(self.base_path, "stim", "MTB_child.wav")
        noise, fs = sf.read(noise_path)

        if noise.ndim > 1:
            noise = np.mean(noise, axis=1)

        rand_start = np.random.randint(0, len(noise))
        noise = np.concatenate((noise[rand_start:], noise[:rand_start]))

        noise = scale_to_system_calibration(noise, target_spl_noise)

        return noise, fs

    def build_list(
        self,
        list_number,
        target_ear,
        target_spl_word,
        target_spl_dist,
        target_spl_noise
    ):

        trials = []

        noise, noise_fs = self._load_and_prepare_noise(target_spl_noise)
        noise_index = 0

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
            rand_trials = np.sort(
                np.random.choice(np.arange(2, 25), 6, replace=False)
            )
            if np.all(np.diff(rand_trials) > 1):
                valid = True

        distractor_map = dict(zip(rand_trials, selected_distractors))

        word_indices = np.random.permutation(25)

        for trial in range(25):

            word_idx = word_indices[trial]

            word = self._extract_string(
                self.word_lists[word_idx, list_number - 1]
            )

            word_path = os.path.join(
                self.base_path,
                "stim",
                "Female_2",
                f"{word}.wav"
            )

            word_audio, fs = sf.read(word_path)
            word_audio = scale_to_system_calibration(
                word_audio,
                target_spl_word
            )

            delay_samples = int(0.5 * fs)
            word_audio = np.concatenate(
                (np.zeros(delay_samples), word_audio)
            )

            dist_present = 0
            dist_name = "none"
            dist_time = 99999

            if trial in distractor_map:

                dist_present = 1
                dist_name = distractor_map[trial]
                dist_filename = f"{dist_name}-peak_RMS.wav"

                dist_path = os.path.join(
                    self.base_path,
                    "stim",
                    "Distractors_RMSscaled",
                    dist_filename
                )

                dist_audio, dist_fs = sf.read(dist_path)

                if dist_fs != fs:
                    new_len = int(len(dist_audio) * fs / dist_fs)
                    dist_audio = resample(dist_audio, new_len)

                dist_audio = scale_to_system_calibration(
                    dist_audio,
                    target_spl_dist
                )

                max_jitter_samples = int(0.75 * fs)
                jitter = np.random.randint(0, max_jitter_samples)

                dist_time = jitter

                dist_audio = np.concatenate(
                    (np.zeros(jitter), dist_audio)
                )

                if len(dist_audio) > len(word_audio):
                    word_audio = np.concatenate(
                        (word_audio,
                         np.zeros(len(dist_audio) - len(word_audio)))
                    )
                else:
                    dist_audio = np.concatenate(
                        (dist_audio,
                         np.zeros(len(word_audio) - len(dist_audio)))
                    )

            else:
                dist_audio = np.zeros_like(word_audio)

            if target_ear == 2:
                stimulus = np.column_stack((dist_audio, word_audio))
            else:
                stimulus = np.column_stack((word_audio, dist_audio))

            stim_len = stimulus.shape[0]

            if noise_index + stim_len > len(noise):
                remaining = len(noise) - noise_index
                noise_segment = np.concatenate(
                    (noise[noise_index:], noise[:stim_len - remaining])
                )
                noise_index = stim_len - remaining
            else:
                noise_segment = noise[
                    noise_index:noise_index + stim_len
                ]
                noise_index += stim_len

            noise_stereo = np.column_stack(
                (noise_segment, noise_segment)
            )

            stimulus = stimulus + noise_stereo

            max_val = np.max(np.abs(stimulus))
            if max_val > 1.0:
                stimulus = stimulus / max_val

            trial_data = {
                "stimulus": stimulus,
                "word": word,
                "dist_present": dist_present,
                "dist_name": dist_name,
                "dist_time": dist_time,
                "target_ear": target_ear
            }

            trials.append(trial_data)

        return trials
