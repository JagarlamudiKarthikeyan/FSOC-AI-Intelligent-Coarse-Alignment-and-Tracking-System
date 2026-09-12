import numpy as np
import cv2


class Disturbances:
    def __init__(self, cfg):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed + 7)
        self.vx = 0.0
        self.vy = 0.0
        self.tx = 0.0
        self.ty = 0.0
        alpha = 0.97
        self._vscale = cfg.jitter_deg * np.sqrt(1.0 - alpha ** 2)
        self._tscale = cfg.turbulence_px * np.sqrt(1.0 - 0.95 ** 2)
        self._alpha = alpha

    def vibration(self):
        if not self.cfg.disturbances:
            return (0.0, 0.0)
        self.vx = self._alpha * self.vx + self.rng.normal(0.0, self._vscale)
        self.vy = self._alpha * self.vy + self.rng.normal(0.0, self._vscale)
        return (self.vx, self.vy)

    def turbulence(self):
        if not self.cfg.disturbances:
            return (0.0, 0.0)
        self.tx = 0.95 * self.tx + self.rng.normal(0.0, self._tscale)
        self.ty = 0.95 * self.ty + self.rng.normal(0.0, self._tscale)
        return (self.tx, self.ty)

    def apply(self, frame):
        if not self.cfg.disturbances:
            return frame
        if self.cfg.blur > 1:
            k = (self.cfg.blur | 1, self.cfg.blur | 1)
            cv2.GaussianBlur(frame, k, 0, dst=frame)
        if self.cfg.noise > 0.0:
            noise = self.rng.normal(0.0, self.cfg.noise * 255.0, frame.shape)
            frame[:] = np.clip(frame.astype(np.float32) + noise, 0.0, 255.0).astype(np.uint8)
        return frame