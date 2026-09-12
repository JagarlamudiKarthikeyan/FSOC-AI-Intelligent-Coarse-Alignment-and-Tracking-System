import math
from collections import deque

from .camera_model import angular_sep


class Metrics:
    def __init__(self, cfg, keep=400):
        self.cfg = cfg
        self.keep = keep
        self.err_deg = deque(maxlen=keep)
        self.err_meas_deg = deque(maxlen=keep)
        self.frames = 0
        self.det_frames = 0
        self.locked_frames = 0
        self.is_locked = False
        self.fps = 0.0
        self.vision_ms = 0.0
        self.frame_ms = 0.0
        self.peak_err_deg = 0.0

    def update(self, t, gt, cam, det_kalman, det_raw, vision_ms, frame_ms, state):
        self.frames += 1
        if det_raw is not None:
            self.det_frames += 1
        self.vision_ms = 0.8 * self.vision_ms + 0.2 * vision_ms
        self.frame_ms = 0.8 * self.frame_ms + 0.2 * frame_ms
        err = None
        measured = None
        if gt is not None:
            err = angular_sep(cam.pan, cam.tilt, gt[0], gt[1])
            self.err_deg.append(err)
            self.peak_err_deg = max(self.peak_err_deg, err)
        if det_kalman is not None:
            az_c, el_c = cam.pixel_to_angles(det_kalman[0], det_kalman[1])
            measured = math.degrees(math.hypot(az_c, el_c))
            self.err_meas_deg.append(measured)
        else:
            self.err_meas_deg.append(None)

        if err is None and measured is not None:
            self.err_deg.append(measured)
            self.peak_err_deg = max(self.peak_err_deg, measured)
        lock_err = err if err is not None else measured
        if lock_err is not None and lock_err < self.cfg.lock_threshold_deg:
            self.locked_frames += 1
        else:
            self.locked_frames = 0
        self.is_locked = self.locked_frames >= self.cfg.lock_frames

    def set_fps(self, fps):
        self.fps = 0.8 * self.fps + 0.2 * fps

    def det_rate(self):
        if self.frames == 0:
            return 0.0
        return 100.0 * self.det_frames / self.frames

    def last_err(self):
        return self.err_deg[-1] if self.err_deg else None

    def summary(self):
        errs = [e for e in self.err_deg if e is not None]
        return {
            "frames": self.frames,
            "fps": round(self.fps, 1),
            "vision_ms": round(self.vision_ms, 2),
            "frame_ms": round(self.frame_ms, 2),
            "detection_rate_pct": round(self.det_rate(), 1),
            "locked": self.is_locked,
            "mean_err_deg": round(sum(errs) / len(errs), 3) if errs else None,
            "peak_err_deg": round(self.peak_err_deg, 3),
            "last_err_deg": round(self.last_err(), 3) if errs else None,
        }