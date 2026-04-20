import os
import shutil
import json
import platform
from datetime import datetime
import soundfile as sf
import csv


class DataManager:
    """
    Handles session-level file organization and data saving for the experiment.

    Responsibilities:
    - create and maintain the subject/visit data folder,
    - store behavioral trial data in CSV format,
    - save trial recordings as WAV files,
    - write session metadata,
    - save questionnaire responses.
    """

    def __init__(self, subject_id, visit, run, snr, dist_cond,
                 target_spl_word, target_spl_dist,
                 list_number, target_ear):

        # Session identifiers and experiment condition values
        self.subject_id = subject_id
        self.visit = str(visit)
        self.run = run
        self.snr = snr
        self.dist_cond = dist_cond
        self.target_spl_word = target_spl_word
        self.target_spl_dist = target_spl_dist
        self.list_number = list_number
        self.target_ear = target_ear

        # Base directory for all saved data in this session
        self.root_path = os.getcwd()
        self.base_folder = os.path.join(
            self.root_path,
            "data",
            "DistVRT_v5",
            str(subject_id),
            f"Visit{self.visit}"
        )

        # Create the session folder if it does not already exist
        os.makedirs(self.base_folder, exist_ok=True)

        # Main behavioral output file
        self.behavior_file = os.path.join(
            self.base_folder,
            f"DistVRT_v5_{subject_id}.csv"
        )

        # Questionnaire output file
        self.questionnaire_file = os.path.join(
            self.base_folder,
            f"DistVRT_v5_{subject_id}_Questionnaire.csv"
        )

        # Session metadata file
        self.metadata_file = os.path.join(
            self.base_folder,
            "session_metadata.json"
        )

        # Ensure the behavioral CSV exists and has the correct header
        self._initialize_behavior_file()

    def check_duplicate(self):
        """
        Check whether a matching trial already exists in the behavioral CSV.

        Duplicate detection is based on the main trial-defining parameters:
        SNR, distractor condition, run number, and list number.
        """
        if not os.path.exists(self.behavior_file):
            return False

        with open(self.behavior_file, newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    if (
                        abs(float(row["SNR"]) - float(self.snr)) < 0.01
                        and int(row["DistCond"]) == int(self.dist_cond)
                        and int(row["RunNum"]) == int(self.run)
                        and int(row["ListNum"]) == int(self.list_number)
                    ):
                        return True
                except Exception:
                    # Skip rows that cannot be parsed cleanly
                    continue

        return False

    def delete_existing(self):
        """Delete existing session data and reinitialize the folder structure."""
        if os.path.exists(self.base_folder):
            shutil.rmtree(self.base_folder)
        os.makedirs(self.base_folder, exist_ok=True)
        self._initialize_behavior_file()

    def overwrite_session(self):
        """Compatibility alias used by older calling code."""
        self.delete_existing()

    def save_metadata(self):
        """
        Save a JSON file describing the current session configuration.

        This is useful for documenting the exact experimental context
        associated with a given subject/visit/run.
        """
        metadata = {
            "subject_id": self.subject_id,
            "visit": self.visit,
            "run": self.run,
            "snr": self.snr,
            "dist_cond": self.dist_cond,
            "target_spl_word": self.target_spl_word,
            "target_spl_dist": self.target_spl_dist,
            "list_number": self.list_number,
            "target_ear": self.target_ear,
            "timestamp": datetime.now().isoformat(),
            "python_version": platform.python_version(),
            "os": platform.system()
        }

        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f, indent=4)

    def _initialize_behavior_file(self):
        """
        Create the behavioral CSV file with a header if it does not yet exist.

        The column structure is designed to support downstream analysis and
        consistent export across subjects and sessions.
        """
        if not os.path.exists(self.behavior_file):
            with open(self.behavior_file, "w") as f:
                header = (
                    "ObsName,TimeStamp,VisitNum,WordLevel,NoiseCond,SNR,"
                    "DistCond,DistLevel,DistTime,RunNum,TrialNum,"
                    "StimTalker,ListNum,StimWord,DistPresent,"
                    "DistItem,TargetSide,Response\n"
                )
                f.write(header)

    def save_trial(self, trial_number, trial_info, response, recording, fs):
        """
        Save one behavioral trial and its corresponding audio recording.

        Parameters
        ----------
        trial_number : int
            Trial index within the current run.

        trial_info : dict
            Trial metadata such as word, distractor name, and distractor timing.

        response : any
            Participant response recorded for the trial.

        recording : array-like
            Recorded audio waveform for the trial.

        fs : int
            Sampling rate used when saving the waveform.
        """
        # Unique timestamp for the trial entry
        timestamp = datetime.now().strftime("DAT_%y_%m_%d_%H_%M_%S")

        # Format one row matching the behavioral CSV structure
        row = (
            f"{self.subject_id},"
            f"{timestamp},"
            f"{self.visit},"
            f"{self.target_spl_word},"
            f"1,"
            f"{self.snr},"
            f"{self.dist_cond},"
            f"{self.target_spl_dist},"
            f"{trial_info['dist_time']},"
            f"{self.run},"
            f"{trial_number},"
            f"Female_2,"
            f"{self.list_number},"
            f"{trial_info['word']},"
            f"{trial_info['dist_present']},"
            f"{trial_info['dist_name']},"
            f"{self.target_ear},"
            f"{response}\n"
        )

        # Append the trial row to the behavioral CSV
        with open(self.behavior_file, "a") as f:
            f.write(row)

        # Construct a stable filename for the recorded waveform
        wav_name = (
            f"{self.subject_id}_"
            f"{self.snr}_"
            f"{self.dist_cond}_"
            f"{self.run}_"
            f"{trial_number}.wav"
        )

        # Save the recorded audio into the session folder
        wav_path = os.path.join(self.base_folder, wav_name)
        sf.write(wav_path, recording, fs)

    def save_questionnaire(self, answers, question_texts):
        """
        Save questionnaire responses to CSV.

        The header is written only once, on the first save, so repeated calls
        append new participant responses cleanly.
        """
        timestamp = datetime.now().strftime("DAT_%y_%m_%d_%H_%M_%S")

        # Check whether the questionnaire file already exists
        file_exists = os.path.exists(self.questionnaire_file)

        with open(self.questionnaire_file, "a", newline="") as f:
            writer = csv.writer(f)

            # Write header on first use
            if not file_exists:
                header = [
                    "ObsName",
                    "TimeStamp",
                    "VisitNum",
                    "RunNum",
                    "ListNum",
                    "SNR",
                    "DistCond"
                ] + question_texts

                writer.writerow(header)

            # Save one row of questionnaire responses
            writer.writerow([
                self.subject_id,
                timestamp,
                self.visit,
                self.run,
                self.list_number,
                self.snr,
                self.dist_cond,
                *answers
            ])
