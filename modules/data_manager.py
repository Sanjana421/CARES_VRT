import os
import shutil
import json
import platform
from datetime import datetime
import soundfile as sf
import csv


class DataManager:

    def __init__(self, subject_id, visit, run, snr, dist_cond,
                 target_spl_word, target_spl_dist,
                 list_number, target_ear):

        self.subject_id = subject_id
        self.visit = str(visit)
        self.run = run
        self.snr = snr
        self.dist_cond = dist_cond
        self.target_spl_word = target_spl_word
        self.target_spl_dist = target_spl_dist
        self.list_number = list_number
        self.target_ear = target_ear

        self.root_path = os.getcwd()
        self.base_folder = os.path.join(
            self.root_path,
            "data",
            "DistVRT_v5",
            str(subject_id),
            f"Visit{self.visit}"
        )

        os.makedirs(self.base_folder, exist_ok=True)

        self.behavior_file = os.path.join(
            self.base_folder,
            f"DistVRT_v5_{subject_id}.csv"
        )

        self.questionnaire_file = os.path.join(
            self.base_folder,
            f"DistVRT_v5_{subject_id}_Questionnaire.csv"
        )

        self.metadata_file = os.path.join(
            self.base_folder,
            "session_metadata.json"
        )

        self._initialize_behavior_file()

    def check_duplicate(self):

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
                    continue

        return False

    def delete_existing(self):
        """Delete existing session data and reinitialise — called by main.py on overwrite."""
        if os.path.exists(self.base_folder):
            shutil.rmtree(self.base_folder)
        os.makedirs(self.base_folder, exist_ok=True)
        self._initialize_behavior_file()

    def overwrite_session(self):
        """Alias kept for compatibility."""
        self.delete_existing()

    def save_metadata(self):

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

        timestamp = datetime.now().strftime("DAT_%y_%m_%d_%H_%M_%S")

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

        with open(self.behavior_file, "a") as f:
            f.write(row)

        wav_name = (
            f"{self.subject_id}_"
            f"{self.snr}_"
            f"{self.dist_cond}_"
            f"{self.run}_"
            f"{trial_number}.wav"
        )

        wav_path = os.path.join(self.base_folder, wav_name)
        sf.write(wav_path, recording, fs)

    def save_questionnaire(self, answers, question_texts):

        timestamp = datetime.now().strftime("DAT_%y_%m_%d_%H_%M_%S")

        file_exists = os.path.exists(self.questionnaire_file)

        with open(self.questionnaire_file, "a", newline="") as f:
            writer = csv.writer(f)

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