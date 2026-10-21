"""
Saves data in EXACTLY the MATLAB DistVRT_v5 format so the scoring system can read
Python-collected sessions the same way as MATLAB ones:

  <data>\\<ID>\\Visit<N>\\DistVRT_v5_<ID>             log, no extension, ", " separators, LF
  <data>\\<ID>\\Visit<N>\\<ID>_<SNR>_<Dist>_<Run>_<Trial>.wav   16-bit mono 44.1 kHz

Like MATLAB (ComputeAndReport), the 25 log rows of a list are written together at the
end of the list with one shared TimeStamp.  While the list is running each trial is also
appended to  <ID>\\Extras\\  as a crash-recovery copy.
Overwrite replaces only the matching run (other runs are kept).
Questionnaires are saved in <data>\\Questionnaires\\.
"""
import os
import queue
import re
import shutil
import threading
from datetime import datetime

import numpy as np
import soundfile as sf

from modules import paths

HEADER = paths.HEADER
N_TRIALS = 25
_BAD_ID = re.compile(r'[\\/:*?"<>|\s]')


def _fmt_disttime(v):
    v = float(v)
    if v == 99999:
        return "99999"
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class DataManager:
    def __init__(self, subject_id, visit, run, snr, dist_cond,
                 target_spl_word, target_spl_dist, list_number, target_ear,
                 noise_cond=1):
        subject_id = str(subject_id).strip()
        if not subject_id or _BAD_ID.search(subject_id):
            raise ValueError("Subject ID must not be empty or contain spaces or any of "
                             "\\ / : * ? \" < > |")
        self.subject_id = subject_id
        self.visit = int(visit)
        self.run = int(run)
        self.snr = float(snr)
        self.dist_cond = int(dist_cond)
        self.target_spl_word = target_spl_word
        self.target_spl_dist = target_spl_dist
        self.list_number = int(list_number)
        self.target_ear = int(target_ear)
        self.noise_cond = int(noise_cond)

        self.visit_folder = paths.visit_dir(subject_id, self.visit)
        self.log_path = paths.log_file(subject_id, self.visit)
        self.extras_folder = paths.extras_dir(subject_id)
        os.makedirs(self.visit_folder, exist_ok=True)
        os.makedirs(self.extras_folder, exist_ok=True)

        self._stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._rows = {}                 # trial_number -> row fields (without TimeStamp)
        self._saved_wavs = []
        self._queue = queue.Queue()
        self._writer = None
        self._write_error = None
        self.recovery_path = os.path.join(
            self.extras_folder, "in_progress_%s_%s_%s_%s.csv" % (
                paths.matlab_num2str(self.snr), self.dist_cond, self.run, self._stamp))

    # ------------------------------------------------------------ naming
    def wav_path(self, trial):
        return os.path.join(self.visit_folder, paths.wav_name(
            self.subject_id, self.snr, self.dist_cond, self.run, trial))

    def _wav_regex(self):
        return re.compile(r"^%s_%s_%d_%d_\d+\.wav$" % (
            re.escape(self.subject_id), re.escape(paths.matlab_num2str(self.snr)),
            self.dist_cond, self.run), re.IGNORECASE)

    # --------------------------------------------------------- log parsing
    def _read_log_lines(self):
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path, encoding="utf-8", errors="replace", newline="") as f:
            return f.read().splitlines()

    def _row_matches(self, line):
        p = [x.strip() for x in line.split(",")]
        if len(p) < 13:
            return False
        try:
            return (abs(float(p[5]) - self.snr) < 0.005 and int(float(p[6])) == self.dist_cond
                    and int(float(p[9])) == self.run and int(float(p[12])) == self.list_number)
        except ValueError:
            return False

    def _matching_wavs(self):
        rx = self._wav_regex()
        return [f for f in os.listdir(self.visit_folder) if rx.match(f)]

    def check_duplicate(self):
        """Same test as DistVRT_Integration.m (SNR, DistCond, Run, List), plus a check
        for recordings that would be overwritten."""
        for line in self._read_log_lines()[1:]:
            if self._row_matches(line):
                return True
        return bool(self._matching_wavs())

    def delete_existing(self):
        """Overwrite: replace ONLY this condition (same SNR / DistCond / Run / List).
        Its recordings and its log rows are removed; other runs are left untouched."""
        for f in self._matching_wavs():
            os.remove(os.path.join(self.visit_folder, f))
        lines = self._read_log_lines()
        if lines:
            kept = [lines[0]] + [l for l in lines[1:] if l.strip() and not self._row_matches(l)]
            with open(self.log_path, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(kept) + "\n")

    def overwrite_session(self):
        """Called by main.py on overwrite."""
        self.delete_existing()

    def save_metadata(self):
        """MATLAB writes no metadata file, so nothing is written."""
        return

    def _row_fields(self, trial_number, info, response):
        n2s = paths.matlab_num2str
        return [
            self.subject_id, None, str(self.visit), n2s(self.target_spl_word),
            str(self.noise_cond), n2s(self.snr), str(self.dist_cond),
            n2s(self.target_spl_dist), _fmt_disttime(info["dist_time"]), str(self.run),
            str(int(trial_number)), paths.TALKER, str(self.list_number), info["word"],
            str(int(info["dist_present"])), info["dist_name"], str(self.target_ear),
            str(response),
        ]

    def save_trial(self, trial_number, trial_info, response, recording, fs):
        """Queue the recording + row for writing and return IMMEDIATELY, so the next
        word starts with no pause even when the data folder is on the server.
        A background thread does the file writing; finalize_list() waits for it."""
        if self._write_error:
            raise OSError(self._write_error)
        rec = np.clip(np.asarray(recording, dtype=np.float32), -1.0, 1.0).copy()
        fields = self._row_fields(trial_number, trial_info, response)
        self._rows[int(trial_number)] = fields
        self._ensure_writer()
        self._queue.put((int(trial_number), rec, int(fs), fields))

    def _ensure_writer(self):
        if self._writer is None or not self._writer.is_alive():
            self._writer = threading.Thread(target=self._write_loop, daemon=True)
            self._writer.start()

    def _write_loop(self):
        while True:
            job = self._queue.get()
            try:
                if job is None:
                    return
                trial_number, rec, fs, fields = job
                if self._write_error:
                    continue
                final = self.wav_path(trial_number)
                tmp = final + ".tmp"
                sf.write(tmp, rec, fs, format="WAV", subtype="PCM_16")
                os.replace(tmp, final)
                self._saved_wavs.append(final)
                stamp = datetime.now().strftime("DAT_%y_%m_%d_%H_%M_%S")
                new = not os.path.exists(self.recovery_path)
                with open(self.recovery_path, "a", encoding="utf-8", newline="\n") as f:
                    if new:
                        f.write(HEADER + "\n")
                    f.write(", ".join(stamp if x is None else x for x in fields) + "\n")
            except Exception as exc:                                  # noqa: BLE001
                self._write_error = str(exc)
            finally:
                self._queue.task_done()

    def wait_for_writes(self):
        """Block until every queued recording has been written."""
        self._queue.join()
        if self._write_error:
            raise OSError(self._write_error)

    def finalize_list(self):
        """Append the list's rows to DistVRT_v5_<ID> (called after trial 25)."""
        self.wait_for_writes()
        stamp = datetime.now().strftime("DAT_%y_%m_%d_%H_%M_%S")
        rows = [self._rows[k] for k in sorted(self._rows)]
        new = not os.path.exists(self.log_path)
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as f:
            if new:
                f.write(HEADER + "\n")
            for r in rows:
                f.write(", ".join(stamp if x is None else x for x in r) + "\n")
            f.flush()
            os.fsync(f.fileno())
        if len(rows) == N_TRIALS and os.path.exists(self.recovery_path):
            os.remove(self.recovery_path)
        return self.log_path

    def save_questionnaire(self, answers, question_texts):
        """Same style as the MATLAB log: no extension, ', ' separators, LF, header ending
        in ', ', num2str numbers.  Saved in <data>\\Questionnaires\\."""
        qdir = paths.questionnaire_dir()
        os.makedirs(qdir, exist_ok=True)
        path = os.path.join(qdir, "%s_%s_Questionnaire" % (
            paths.LOG_PREFIX, self.subject_id))
        clean = lambda x: str(x).replace(",", ";").replace("\n", " ")        # noqa: E731
        new = not os.path.exists(path)
        stamp = datetime.now().strftime("DAT_%y_%m_%d_%H_%M_%S")
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            if new:
                f.write("".join(clean(x) + ", " for x in ["ObsName", "TimeStamp", "VisitNum",
                        "RunNum", "ListNum", "SNR", "DistCond"] + list(question_texts)) + "\n")
            f.write("".join(clean(x) + ", " for x in [
                self.subject_id, stamp, self.visit, self.run, self.list_number,
                paths.matlab_num2str(self.snr), self.dist_cond] + list(answers)) + "\n")
