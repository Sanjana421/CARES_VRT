import os
import numpy as np
import soundfile as sf
from scipy.io import loadmat
from scipy.signal import resample as scipy_resample

from modules.calibration import scale_to_system_calibration

TARGET_FS = 44100   # MOTU M Series native sample rate (matches MATLAB FS_MOTU)


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
        """Read a wav file and return (mono_float64_array, sample_rate)."""
        audio, fs = sf.read(path)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        return audio, fs

    def _resample_to_target(self, audio, fs):
        """Resample to TARGET_FS if needed — matches MATLAB's per-trial resample()."""
        if fs == TARGET_FS:
            return audio
        new_len = int(len(audio) * TARGET_FS / fs)
        return scipy_resample(audio, new_len)

    def _load_and_prepare_noise(self, target_spl_noise):
        """
        Load MTB_child.wav, randomise start point, scale to target SPL.
        Matches MATLAB MakeStim noise block exactly.
        Returns noise at TARGET_FS so it can be mixed with resampled stimuli.
        """
        noise, fs = self._read_mono(
            os.path.join(self.base_path, "stim", "MTB_child.wav")
        )
        # Randomise start point (MATLAB: tmp = randi(length(all_noise)))
        rand_start = np.random.randint(0, len(noise))
        noise = np.concatenate((noise[rand_start:], noise[:rand_start]))
        noise = scale_to_system_calibration(noise, target_spl_noise)
        # Resample noise to TARGET_FS so lengths match word audio
        noise = self._resample_to_target(noise, fs)
        return noise

    def build_list(
        self,
        list_number,
        target_ear,
        target_spl_word,
        target_spl_dist,
        target_spl_noise,
        distractor_condition=1
    ):
        trials = []

        noise       = self._load_and_prepare_noise(target_spl_noise)
        noise_index = 0

        # ── Distractor selection (matches MATLAB randperm logic) ──────────────
        # MATLAB: unpleasant 1-15, neutral 16-24, pleasant 25-39  (1-indexed)
        # Python: unpleasant 0-14, neutral 15-23, pleasant 24-38  (0-indexed)
        unpleasant = np.random.choice(np.arange(0,  15), 2, replace=False)
        neutral    = np.random.choice(np.arange(15, 24), 2, replace=False)
        pleasant   = np.random.choice(np.arange(24, 39), 2, replace=False)

        selected_indices = np.concatenate([unpleasant, neutral, pleasant])
        np.random.shuffle(selected_indices)

        selected_distractors = [
            self._extract_string(self.distractor_list[i])
            for i in selected_indices
        ]

        # ── Distractor trial positions (no consecutive trials) ────────────────
        # MATLAB: randsample(3:25, 6) → 1-indexed → Python 0-indexed = arange(2,25)
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

            # Load word, force mono, calibrate, resample to TARGET_FS
            word_audio, word_fs = self._read_mono(
                os.path.join(self.base_path, "stim", "Female_2", f"{word}.wav")
            )
            word_audio = scale_to_system_calibration(word_audio, target_spl_word)
            word_audio = self._resample_to_target(word_audio, word_fs)

            # 500 ms silence before word onset (MATLAB: stim_delay_s = 0.500)
            delay_samples = int(0.5 * TARGET_FS)
            word_audio    = np.concatenate((np.zeros(delay_samples), word_audio))

            dist_present = 0
            dist_name    = "none"
            dist_time    = 99999   # sentinel = no distractor (matches MATLAB)

            if trial in distractor_map:
                dist_present  = 1
                dist_name     = distractor_map[trial]
                dist_filename = f"{dist_name}-peak_RMS.wav"

                dist_audio, dist_fs = self._read_mono(
                    os.path.join(
                        self.base_path,
                        "stim", "Distractors_RMSscaled",
                        dist_filename
                    )
                )
                dist_audio = scale_to_system_calibration(dist_audio, target_spl_dist)
                dist_audio = self._resample_to_target(dist_audio, dist_fs)

                # Random jitter — MATLAB: distwindow=18311 @ ~24414Hz ≈ 750ms
                max_jitter = int(0.75 * TARGET_FS)
                jitter     = np.random.randint(1, max_jitter + 1)  # randi(N) = 1..N

                # dist_time: ms relative to word onset (matches MATLAB log format)
                # MATLAB: if jit >= stim_delay → positive (after word onset)
                #         else                 → negative (before word onset)
                if jitter >= delay_samples:
                    dist_time = ((jitter / TARGET_FS) * 1000) - 500
                else:
                    dist_time = -((jitter / TARGET_FS) * 1000)

                dist_audio = np.concatenate((np.zeros(jitter), dist_audio))

                # Pad shorter array so both are same length
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

            # ── Stereo assembly (matches MATLAB channel mapping) ──────────────
            # MATLAB target_ear==2 → [dist, word] = dist on L (ch3), word on R (ch4)
            # MATLAB else          → [word, dist] = word on L (ch3), dist on R (ch4)
            if target_ear == 2:
                stimulus = np.column_stack((dist_audio, word_audio))
            else:
                stimulus = np.column_stack((word_audio, dist_audio))

            # ── Add noise segment ─────────────────────────────────────────────
            # MATLAB plays noise as a SEPARATE continuous audioplayer alongside
            # the speech. We approximate this by mixing a matching-length noise
            # segment into each trial. Calibration levels are preserved — no
            # post-hoc normalisation (that would destroy the SNR).
            stim_len = stimulus.shape[0]

            if noise_index + stim_len > len(noise):
                remaining     = len(noise) - noise_index
                noise_segment = np.concatenate(
                    (noise[noise_index:], noise[:stim_len - remaining])
                )
                noise_index = stim_len - remaining
            else:
                noise_segment = noise[noise_index:noise_index + stim_len]
                noise_index  += stim_len

            noise_stereo = np.column_stack((noise_segment, noise_segment))
            stimulus     = stimulus + noise_stereo

            # Cast to float32 for audio output
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
