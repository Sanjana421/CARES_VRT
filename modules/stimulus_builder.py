import os
import numpy as np
import soundfile as sf
from scipy.io import loadmat
from scipy.signal import resample_poly
from math import gcd

from modules.calibration import scale_to_system_calibration

TARGET_FS = 44100   # MOTU M Series native sample rate


class StimulusBuilder:

    def __init__(self, base_path):
        self.base_path       = base_path
        self.word_lists      = self._load_word_lists()
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
        """Read a wav file, force mono, return (float64 array, sample_rate)."""
        audio, fs = sf.read(path)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        return audio, fs

    def _resample_to_target(self, audio, fs):
        """
        Resample to TARGET_FS using polyphase filtering.
        Matches MATLAB's resample() which also uses polyphase (not FFT).
        """
        if fs == TARGET_FS:
            return audio
        g   = gcd(TARGET_FS, fs)
        up  = TARGET_FS // g
        down = fs // g
        return resample_poly(audio, up, down)

    def _load_and_prepare_noise(self, target_spl_noise):
        """
        Load MTB_child.wav, randomise start point, calibrate, resample.
        Matches MATLAB MakeStim noise block exactly.
        """
        noise, fs = self._read_mono(
            os.path.join(self.base_path, "stim", "MTB_child.wav")
        )
        rand_start = np.random.randint(0, len(noise))
        noise      = np.concatenate((noise[rand_start:], noise[:rand_start]))
        noise      = scale_to_system_calibration(noise, target_spl_noise)
        noise      = self._resample_to_target(noise, fs)
        return noise

    def build_list(
        self,
        list_number,
        target_ear,
        target_spl_word,
        target_spl_dist,
        target_spl_noise
    ):
        trials = []

        noise       = self._load_and_prepare_noise(target_spl_noise)
        noise_index = 0

        # ── Distractor selection ──────────────────────────────────────────────
        # MATLAB: unpleasant 1-15, neutral 16-24, pleasant 25-39 (1-indexed)
        # Python: unpleasant 0-14, neutral 15-23, pleasant 24-38 (0-indexed)
        unpleasant = np.random.choice(np.arange(0,  15), 2, replace=False)
        neutral    = np.random.choice(np.arange(15, 24), 2, replace=False)
        pleasant   = np.random.choice(np.arange(24, 39), 2, replace=False)

        selected_indices     = np.concatenate([unpleasant, neutral, pleasant])
        np.random.shuffle(selected_indices)
        selected_distractors = [
            self._extract_string(self.distractor_list[i])
            for i in selected_indices
        ]

        # ── Distractor trial positions (no consecutive trials) ────────────────
        valid = False
        while not valid:
            rand_trials = np.sort(
                np.random.choice(np.arange(2, 25), 6, replace=False)
            )
            if np.all(np.diff(rand_trials) > 1):
                valid = True

        distractor_map = dict(zip(rand_trials, selected_distractors))

        # ── Word order ────────────────────────────────────────────────────────
        word_indices = np.random.permutation(25)

        # ── Build each trial ──────────────────────────────────────────────────
        for trial in range(25):

            word_idx = word_indices[trial]
            word     = self._extract_string(
                self.word_lists[word_idx, list_number - 1]
            )

            # Load word → calibrate → resample → prepend 500ms silence
            word_audio, word_fs = self._read_mono(
                os.path.join(self.base_path, "stim", "Female_2", f"{word}.wav")
            )
            word_audio    = scale_to_system_calibration(word_audio, target_spl_word)
            word_audio    = self._resample_to_target(word_audio, word_fs)
            delay_samples = int(0.5 * TARGET_FS)
            word_audio    = np.concatenate((np.zeros(delay_samples), word_audio))

            dist_present = 0
            dist_name    = "none"
            dist_time    = 99999

            if trial in distractor_map:
                dist_present  = 1
                dist_name     = distractor_map[trial]

                dist_audio, dist_fs = self._read_mono(
                    os.path.join(
                        self.base_path,
                        "stim", "Distractors_RMSscaled",
                        f"{dist_name}-peak_RMS.wav"
                    )
                )
                dist_audio = scale_to_system_calibration(dist_audio, target_spl_dist)
                dist_audio = self._resample_to_target(dist_audio, dist_fs)

                # Jitter: MATLAB randi(N) = 1..N
                max_jitter = int(0.75 * TARGET_FS)
                jitter     = np.random.randint(1, max_jitter + 1)

                # dist_time in ms relative to word onset (matches MATLAB log)
                if jitter >= delay_samples:
                    dist_time = ((jitter / TARGET_FS) * 1000) - 500
                else:
                    dist_time = -((jitter / TARGET_FS) * 1000)

                dist_audio = np.concatenate((np.zeros(jitter), dist_audio))

                # Pad to equal length
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

            # ── Stereo assembly ───────────────────────────────────────────────
            # target_ear==2 → dist L (ch3), word R (ch4)
            # else          → word L (ch3), dist R (ch4)
            if target_ear == 2:
                stimulus = np.column_stack((dist_audio, word_audio))
            else:
                stimulus = np.column_stack((word_audio, dist_audio))

            # ── Mix noise segment (CONTINUOUS + SMOOTH) ───────────────────────
            stim_len = stimulus.shape[0]

            # Wrap-around safe indexing
            end_idx = noise_index + stim_len

            if end_idx <= len(noise):
                noise_segment = noise[noise_index:end_idx]
            else:
                part1 = noise[noise_index:]
                part2 = noise[:end_idx - len(noise)]
                noise_segment = np.concatenate((part1, part2))

            # Advance pointer globally (continuous across trials)
            noise_index = end_idx % len(noise)

            # Slight scaling to prevent masking (IMPORTANT)
            #noise_stereo = np.column_stack((noise_segment, noise_segment))

            # MIX (balanced)
            #stimulus = stimulus + 0.35 * noise_stereo

            # Soft clip to [-1, 1] to protect amplifier — preserves calibration
            # ratios, only prevents clipping distortion on loud distractor trials
            stimulus = np.clip(stimulus, -1.0, 1.0)

            stimulus = stimulus.astype(np.float32)

            trials.append({
                "stimulus":     stimulus,
                "word":         word,
                "dist_present": dist_present,
                "dist_name":    dist_name,
                "dist_time":    dist_time,
                "target_ear":   target_ear
            })

        return trials
