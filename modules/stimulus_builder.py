import os
import numpy as np
import soundfile as sf
from scipy.io import loadmat
from scipy.signal import resample_poly

from modules.calibration import scale_to_system_calibration


TARGET_FS = 44100  # MOTU native rate (must match AudioEngine)


class StimulusBuilder:

    def __init__(self, base_path):
        self.base_path = base_path
        self.word_lists = self._load_word_lists()
        self.distractor_list = self._load_distractor_list()

    # ------------------------------------------------------------------
    # DATA LOADERS
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # AUDIO UTILITIES
    # ------------------------------------------------------------------

    def _read_mono(self, path):
        audio, fs = sf.read(path)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        return audio.astype(np.float32), fs

    def _resample_to_target(self, audio, fs):
        if fs == TARGET_FS:
            return audio
        return resample_poly(audio, TARGET_FS, fs)

    # ------------------------------------------------------------------
    # NOISE PREP (continuous across trials)
    # ------------------------------------------------------------------

    def _prepare_noise(self, target_spl_noise):
        noise, fs = self._read_mono(
            os.path.join(self.base_path, "stim", "MTB_child.wav")
        )

        # randomize starting point (MATLAB equivalent)
        start = np.random.randint(0, len(noise))
        noise = np.concatenate((noise[start:], noise[:start]))

        noise = scale_to_system_calibration(noise, target_spl_noise)
        noise = self._resample_to_target(noise, fs)

        return noise

    # ------------------------------------------------------------------
    # MAIN BUILD FUNCTION
    # ------------------------------------------------------------------

    def build_list(
        self,
        list_number,
        target_ear,
        target_spl_word,
        target_spl_dist,
        target_spl_noise,
        distractor_condition
    ):

        trials = []

        noise = self._prepare_noise(target_spl_noise)
        noise_idx = 0

        # --------------------------------------------------------------
        # DISTRACTOR SELECTION (match MATLAB indexing logic)
        # --------------------------------------------------------------

        unpleasant = np.random.choice(np.arange(0, 15), 2, replace=False)
        neutral = np.random.choice(np.arange(15, 24), 2, replace=False)
        pleasant = np.random.choice(np.arange(24, 39), 2, replace=False)

        selected_indices = np.concatenate((unpleasant, neutral, pleasant))
        np.random.shuffle(selected_indices)

        selected_distractors = [
            self._extract_string(self.distractor_list[i])
            for i in selected_indices
        ]

        # choose 6 non-consecutive trials (MATLAB randsample(3:25))
        distractor_trials = []
        if distractor_condition == 1:
            valid = False
            while not valid:
                rand_trials = np.sort(
                    np.random.choice(np.arange(2, 25), 6, replace=False)
                )
                if np.all(np.diff(rand_trials) > 1):
                    valid = True
            distractor_trials = rand_trials

        distractor_map = dict(zip(distractor_trials, selected_distractors))

        # --------------------------------------------------------------
        # WORD ORDER
        # --------------------------------------------------------------

        word_indices = np.random.permutation(25)

        # --------------------------------------------------------------
        # BUILD EACH TRIAL
        # --------------------------------------------------------------

        for trial in range(25):

            word_idx = word_indices[trial]
            word = self._extract_string(
                self.word_lists[word_idx, list_number - 1]
            )

            word_audio, word_fs = self._read_mono(
                os.path.join(self.base_path, "stim", "Female_2", f"{word}.wav")
            )

            word_audio = scale_to_system_calibration(word_audio, target_spl_word)
            word_audio = self._resample_to_target(word_audio, word_fs)

            # 500 ms delay before word onset
            delay_samples = int(0.5 * TARGET_FS)
            word_audio = np.concatenate((np.zeros(delay_samples), word_audio))

            dist_present = 0
            dist_name = "none"
            dist_time = 99999

            if trial in distractor_map:

                dist_present = 1
                dist_name = distractor_map[trial]

                dist_audio, dist_fs = self._read_mono(
                    os.path.join(
                        self.base_path,
                        "stim",
                        "Distractors_RMSscaled",
                        f"{dist_name}-peak_RMS.wav"
                    )
                )

                dist_audio = scale_to_system_calibration(dist_audio, target_spl_dist)
                dist_audio = self._resample_to_target(dist_audio, dist_fs)

                # jitter up to 750 ms (MATLAB equivalent)
                max_jitter = int(0.75 * TARGET_FS)
                jitter = np.random.randint(1, max_jitter + 1)

                if jitter >= delay_samples:
                    dist_time = ((jitter / TARGET_FS) * 1000) - 500
                else:
                    dist_time = -((jitter / TARGET_FS) * 1000)

                dist_audio = np.concatenate((np.zeros(jitter), dist_audio))

                # pad shorter array
                if len(dist_audio) > len(word_audio):
                    word_audio = np.concatenate(
                        (word_audio, np.zeros(len(dist_audio) - len(word_audio)))
                    )
                else:
                    dist_audio = np.concatenate(
                        (dist_audio, np.zeros(len(word_audio) - len(dist_audio)))
                    )

            else:
                dist_audio = np.zeros_like(word_audio)

            # ----------------------------------------------------------
            # STEREO ROUTING (match MATLAB)
            # ----------------------------------------------------------

            if target_ear == 2:
                stimulus = np.column_stack((dist_audio, word_audio))
            else:
                stimulus = np.column_stack((word_audio, dist_audio))

            # ----------------------------------------------------------
            # ADD CONTINUOUS NOISE SEGMENT
            # ----------------------------------------------------------

            stim_len = stimulus.shape[0]

            if noise_idx + stim_len > len(noise):
                remaining = len(noise) - noise_idx
                noise_segment = np.concatenate(
                    (noise[noise_idx:], noise[:stim_len - remaining])
                )
                noise_idx = stim_len - remaining
            else:
                noise_segment = noise[noise_idx:noise_idx + stim_len]
                noise_idx += stim_len

            noise_stereo = np.column_stack((noise_segment, noise_segment))

            # MIX (no renormalization — preserve SNR)
            stimulus = stimulus + noise_stereo

            # prevent clipping (lab-safe headroom)
            max_val = np.max(np.abs(stimulus))
            if max_val > 0.98:
                stimulus = stimulus / max_val * 0.98

            trials.append({
                "word": word,
                "stimulus": stimulus.astype(np.float32),
                "dist_present": dist_present,
                "dist_name": dist_name,
                "dist_time": dist_time
            })

        return trials