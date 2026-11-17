"""Add completed collection runs to the lab scoring workbook."""

import os
import random
import time

import openpyxl

from modules import paths


LOCK_TIMEOUT = 30
LOCK_POLL = 0.1
STALE_AFTER = 60

EXPECTED_HEADERS = (
    "ObsName",
    "VisitNum",
    "NoiseCond",
    "SNR",
    "DistCond",
    "RunNum",
)


class ScoringLogLock:
    """Use the same .lock sidecar file as the scoring app."""

    def __init__(self, xlsx_path):
        self.lock_path = xlsx_path + ".lock"
        self.acquired = False

    def _remove_if_stale(self):
        try:
            age = time.time() - os.path.getmtime(self.lock_path)
        except FileNotFoundError:
            return

        if age > STALE_AFTER:
            try:
                os.remove(self.lock_path)
            except FileNotFoundError:
                pass

    def acquire(self):
        deadline = time.time() + LOCK_TIMEOUT

        while time.time() < deadline:
            try:
                fd = os.open(
                    self.lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
                os.write(fd, str(os.getpid()).encode("ascii"))
                os.close(fd)
                self.acquired = True
                return
            except FileExistsError:
                self._remove_if_stale()
                time.sleep(LOCK_POLL + random.uniform(0, 0.05))

        raise TimeoutError(
            "Could not access the scoring workbook because another app "
            "is using its lock. Try again in a moment."
        )

    def release(self):
        if self.acquired:
            try:
                os.remove(self.lock_path)
            except FileNotFoundError:
                pass
            self.acquired = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_):
        self.release()


def _as_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _same_run(row_values, expected):
    """Compare workbook columns A–F with the completed collection run."""
    row_subject, row_visit, row_noise, row_snr, row_dist, row_run = row_values
    subject, visit, noise, snr, dist, run = expected

    row_snr_num = _as_number(row_snr)
    expected_snr_num = _as_number(snr)

    return (
        str(row_subject).strip().casefold()
        == str(subject).strip().casefold()
        and _as_number(row_visit) == _as_number(visit)
        and _as_number(row_noise) == _as_number(noise)
        and row_snr_num is not None
        and expected_snr_num is not None
        and abs(row_snr_num - expected_snr_num) < 0.000001
        and _as_number(row_dist) == _as_number(dist)
        and _as_number(row_run) == _as_number(run)
    )


def queue_run_for_scoring(data_manager):
    """Append a run to scoring-log columns A–F.

    Returns "added" or "already_present".
    Raises an exception if the workbook cannot be safely updated.
    """
    xlsx_path = paths.SCORING_LOG_FILE

    if not os.path.isfile(xlsx_path):
        raise FileNotFoundError(
            "The scoring workbook was not found:\n%s" % xlsx_path
        )

    expected = (
        str(data_manager.subject_id),
        int(data_manager.visit),
        int(data_manager.noise_cond),
        float(data_manager.snr),
        int(data_manager.dist_cond),
        int(data_manager.run),
    )

    with ScoringLogLock(xlsx_path):
        workbook = openpyxl.load_workbook(xlsx_path)

        try:
            # The scoring app also uses the active worksheet.
            sheet = workbook.active

            headers = tuple(
                str(sheet.cell(row=1, column=column).value or "").strip()
                for column in range(1, 7)
            )

            if headers != EXPECTED_HEADERS:
                raise ValueError(
                    "The scoring workbook's first six headers do not match "
                    "the expected order. No scoring-log data was changed."
                )

            # Avoid adding a duplicate if this run is already queued.
            for row_number in range(2, sheet.max_row + 1):
                values = tuple(
                    sheet.cell(row=row_number, column=column).value
                    for column in range(1, 7)
                )
                if _same_run(values, expected):
                    return "already_present"

            # Find an unused row. The write below is restricted to A–F.
            row_number = 2
            while row_number <= sheet.max_row:
                row_is_empty = all(
                    sheet.cell(row=row_number, column=column).value in (None, "")
                    for column in range(1, 10)
                )
                if row_is_empty:
                    break
                row_number += 1

            for column, value in enumerate(expected, start=1):
                sheet.cell(row=row_number, column=column).value = value

            workbook.save(xlsx_path)
            return "added"

        finally:
            workbook.close()
