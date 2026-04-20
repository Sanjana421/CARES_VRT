# os:
# Used for file and folder path handling.
# Similar to MATLAB's fullfile and general path utilities.
import os

# numpy:
# Main numerical array library in Python.
# Similar in spirit to MATLAB matrices and vector operations.
import numpy as np

# soundfile:
# Used to read and write WAV/audio files.
# Similar to MATLAB audio read/write functions.
import soundfile as sf

# loadmat:
# Reads .mat files created in MATLAB.
# Used here to load the word lists and distractor lists.
from scipy.io import loadmat

# scipy_resample:
# Resamples audio from one sampling rate to another.
# This is important when source files do not already match the system rate.
from scipy.signal import resample as scipy_resample

# Calibration helper used to scale audio to the system-specific SPL reference.
# This keeps playback levels consistent across the experiment.
from modules.calibration import scale_to_system_calibration

# Target sampling rate for all audio in the experiment.
# All stimuli are converted to this rate so timing remains consistent.
# This must match the audio engine settings.
TARGET_FS = 44100


class StimulusBuilder:
    """
    Builds all trial stimuli for one list.

    Each trial includes:
    - target word audio
    - optional distractor audio
    - correct stereo routing (left/right ear)
    """

    def __init__(self, base_path):
        # Base directory containing the stimulus folders and .mat list files.
        self.base_path = base_path

        # Load the word list matrix from MATLAB.
        # This file contains the trial words arranged in list format.
        self.word_lists = self._load_word_lists()

        # Load the distractor list matrix from MATLAB.
        # These are the distractor items used across trials.
        self.distractor_list = self._load_distractor_list()

    # ─────────────────────────────────────────────
    # LOAD DATA FILES
    # ─────────────────────────────────────────────

    def _load_word_lists(self):
        # Load the MATLAB file containing the balanced word lists.
        # MATLAB .mat files often store arrays in nested structures.
        mat = loadmat(os.path.join(self.base_path, "BalancedWordLists_cell.mat"))
        return mat["BalancedWordLists_cell"]

    def _load_distractor_list(self):
        # Load the MATLAB file containing the distractor list.
        mat = loadmat(os.path.join(self.base_path, "NarrowDistractList_cell.mat"))
        return mat["NarrowDistractList_cell"]

    def _extract_string(self, cell_entry):
        """
        MATLAB .mat files often store strings inside nested array containers.
        This helper unwraps those nested structures into a plain Python string.

        In MATLAB terms, this is similar to indexing down into a cell array
        until the actual text value is reached.
        """
        while isinstance(cell_entry, np.ndarray):
            cell_entry = cell_entry[0]
        return str(cell_entry)

    # ─────────────────────────────────────────────
    # AUDIO UTILITIES
    # ─────────────────────────────────────────────

    def _read_mono(self, path):
        """
        Read an audio file and return a mono float32 waveform.

        If the file is stereo, the channels are averaged to create one
        mono signal for later routing into left/right output channels.
        """
        audio, fs = sf.read(path)

        # Convert stereo to mono if needed.
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        return audio.astype(np.float32), fs

    def _resample_to_target(self, audio, fs):
        """
        Resample audio to the experiment's target sampling rate.

        This is necessary when the original file sample rate differs from the
        system sample rate used for playback and timing.
        """
        if fs == TARGET_FS:
            return audio.astype(np.float32)

        new_len = int(round(len(audio) * TARGET_FS / fs))
        return scipy_resample(audio, new_len).astype(np.float32)

    # ─────────────────────────────────────────────
    # MAIN FUNCTION: BUILD TRIAL LIST
    # ─────────────────────────────────────────────

    def build_list(self, list_number, target_ear,
                   target_spl_word, target_spl_dist,
                   target_spl_noise=None):
        """
        Create a randomized list of 25 trials.

        Randomization includes:
        - word order
        - distractor placement
        - distractor timing within eligible trials

        Notes for MATLAB readers:
        - This is similar to creating a trial struct array or table in a loop.
        - Each trial is stored as a Python dictionary.
        """

        trials = []

        # Select distractors from three categories:
        # unpleasant, neutral, and pleasant.
        # This creates a balanced set across emotional valence.
        unpleasant = np.random.choice(np.arange(0, 15), 2, replace=False)
        neutral = np.random.choice(np.arange(15, 24), 2, replace=False)
        pleasant = np.random.choice(np.arange(24, 39), 2, replace=False)

        selected_indices = np.concatenate([unpleasant, neutral, pleasant])
        np.random.shuffle(selected_indices)

        # Convert MATLAB-style nested entries into plain Python strings.
        selected_distractors = [
            self._extract_string(self.distractor_list[i])
            for i in selected_indices
        ]

        # Choose six trial positions for distractors.
        # The spacing rule avoids consecutive distractor trials.
        valid = False
        while not valid:
            rand_trials = np.sort(np.random.choice(np.arange(2, 25), 6, replace=False))
            if np.all(np.diff(rand_trials) > 1):
                valid = True

        distractor_map = dict(zip(rand_trials, selected_distractors))

        # Randomize the order of the 25 words.
        word_indices = np.random.permutation(25)

        # ─────────────────────────────────────────────
        # BUILD EACH TRIAL
        # ─────────────────────────────────────────────

        for trial in range(25):

            # Select the word assigned to this trial.
            word_idx = word_indices[trial]
            word = self._extract_string(self.word_lists[word_idx, list_number - 1])

            # Load the target word audio from disk.
            word_audio, word_fs = self._read_mono(
                os.path.join(self.base_path, "stim", "Female_2", f"{word}.wav")
            )

            # Resample to the fixed experiment sampling rate.
            word_audio = self._resample_to_target(word_audio, word_fs)

            # Scale word audio to the calibrated system level.
            word_audio = scale_to_system_calibration(word_audio, target_spl_word)

            # Add 500 ms of silence before the word starts.
            # This creates a standard onset delay for all trials.
            delay_samples = int(0.5 * TARGET_FS)
            word_audio = np.concatenate((np.zeros(delay_samples, dtype=np.float32), word_audio))

            # Default values for trials without a distractor.
            dist_present = 0
            dist_name = "none"
            dist_time = 99999

            # Add distractor if this trial is scheduled to have one.
            if trial in distractor_map:
                dist_present = 1
                dist_name = distractor_map[trial]

                # Distractor file naming follows the RMS-scaled convention.
                dist_filename = f"{dist_name}-peak_RMS.wav"

                # Load distractor audio from disk.
                dist_audio, dist_fs = self._read_mono(
                    os.path.join(self.base_path, "stim", "Distractors_RMSscaled", dist_filename)
                )

                # Resample distractor to the experiment rate.
                dist_audio = self._resample_to_target(dist_audio, dist_fs)

                # Scale distractor to the desired SPL.
                dist_audio = scale_to_system_calibration(dist_audio, target_spl_dist)

                # Add random timing jitter up to 750 ms.
                max_jitter = int(0.75 * TARGET_FS)
                jitter = np.random.randint(1, max_jitter + 1)

                # Store distractor onset relative to the word onset.
                # Positive values mean after the word delay,
                # negative values mean before the word onset.
                if jitter >= delay_samples:
                    dist_time = ((jitter / TARGET_FS) * 1000) - 500
                else:
                    dist_time = -((jitter / TARGET_FS) * 1000)

                # Delay distractor onset by the jitter amount.
                dist_audio = np.concatenate((np.zeros(jitter, dtype=np.float32), dist_audio))

                # Make sure both signals are the same length before stereo routing.
                if len(dist_audio) > len(word_audio):
                    word_audio = np.concatenate(
                        (word_audio, np.zeros(len(dist_audio) - len(word_audio), dtype=np.float32))
                    )
                else:
                    dist_audio = np.concatenate(
                        (dist_audio, np.zeros(len(word_audio) - len(dist_audio), dtype=np.float32))
                    )

            else:
                # No distractor for this trial; use silence in the distractor channel.
                dist_audio = np.zeros_like(word_audio, dtype=np.float32)

            # ── Stereo routing ──
            # target_ear controls which channel gets the target word.
            # This is similar to assigning signals to left/right output buses in MATLAB.
            if target_ear == 2:
                stimulus = np.column_stack((dist_audio, word_audio))
            else:
                stimulus = np.column_stack((word_audio, dist_audio))

            # Store all relevant trial information together.
            # In MATLAB, this would be similar to storing fields in a struct array.
            trials.append({
                "stimulus": stimulus.astype(np.float32),
                "word": word,
                "dist_present": dist_present,
                "dist_name": dist_name,
                "dist_time": dist_time,
                "target_ear": target_ear,
            })

        return trials
