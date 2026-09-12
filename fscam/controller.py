import numpy as np

SEARCH = "SEARCH"
TRACK = "TRACK"
LOST = "LOST"


class CoarseController:
    def __init__(self, cfg, camera):
        self.cfg = cfg
        self.cam = camera
        self.kp = cfg.kp
        self.ki = cfg.ki
        self.kd = cfg.kd
        self._ff_alpha = 0.5
        self.state = SEARCH
        self.integral = [0.0, 0.0]
        self.prev_err = [0.0, 0.0]
        self.lost_frames = 0
        self.track_frames = 0
        self.scan_dir = 1
        self.scan_row = 0
        self.center_pan = camera.pan
        self.center_tilt = camera.tilt
        self.ff_az = 0.0
        self.ff_el = 0.0
        self.last_ang = None

    def reset(self, pan, tilt):
        self.center_pan = pan
        self.center_tilt = tilt
        self.integral = [0.0, 0.0]
        self.prev_err = [0.0, 0.0]
        self.state = SEARCH
        self.lost_frames = 0
        self.track_frames = 0
        self.scan_dir = 1
        self.scan_row = 0
        self.ff_az = 0.0
        self.ff_el = 0.0
        self.last_ang = None

    def _pid(self, axis, err, dt):
        self.integral[axis] = float(np.clip(self.integral[axis] + err * dt, -10.0, 10.0))
        d = (err - self.prev_err[axis]) / max(dt, 1e-4)
        self.prev_err[axis] = err
        out = self.kp * err + self.ki * self.integral[axis] + self.kd * d
        return float(np.clip(out, -self.cfg.max_rate_deg_s, self.cfg.max_rate_deg_s))

    def step(self, det, dt, enabled):
        if not enabled:
            return self.state
        cfg = self.cfg
        if det is None:
            self.lost_frames += 1
            if self.state == TRACK and self.lost_frames >= cfg.max_lost:
                self.state = SEARCH
                self.scan_dir = 1
                self.scan_row = 0
                self.integral = [0.0, 0.0]
        else:
            if self.state == SEARCH:
                self.state = TRACK
                self.track_frames = 0
                self.integral = [0.0, 0.0]
                self.prev_err = [0.0, 0.0]
            else:
                self.track_frames += 1
            self.lost_frames = 0

        if self.state != TRACK:
            self.last_ang = None
            self.ff_az = 0.0
            self.ff_el = 0.0

        if self.state == TRACK:
            az_c, el_c = self.cam.pixel_to_angles(det[0], det[1])
            e_az = np.degrees(az_c)
            e_el = np.degrees(el_c)
            cur_ang = (e_az, e_el)
            if self.last_ang is not None:
                daz = cur_ang[0] - self.last_ang[0]
                del_ang = cur_ang[1] - self.last_ang[1]
                a = self._ff_alpha
                self.ff_az = a * (daz / dt) + (1.0 - a) * self.ff_az
                self.ff_el = a * (del_ang / dt) + (1.0 - a) * self.ff_el
            else:
                self.ff_az = 0.0
                self.ff_el = 0.0
            self.last_ang = cur_ang
            v_az = self._pid(0, e_az, dt)
            v_el = self._pid(1, e_el, dt)
            v_az = float(np.clip(v_az + self.ff_az, -self.cfg.max_rate_deg_s, self.cfg.max_rate_deg_s))
            v_el = float(np.clip(v_el + self.ff_el, -self.cfg.max_rate_deg_s, self.cfg.max_rate_deg_s))
            self.cam.set_pose(self.cam.pan + v_az * dt, self.cam.tilt + v_el * dt)
        elif self.state == SEARCH:
            step_pan = cfg.scan_speed_deg_s * dt * self.scan_dir
            lo = self.center_pan - cfg.scan_window_deg / 2.0
            hi = self.center_pan + cfg.scan_window_deg / 2.0
            new_pan = self.cam.pan + step_pan
            if new_pan > hi:
                new_pan = hi
                self.scan_dir = -1
                self.scan_row += 1
            elif new_pan < lo:
                new_pan = lo
                self.scan_dir = 1
                self.scan_row += 1
            if self.scan_row * cfg.scan_row_step_deg > cfg.scan_window_deg / 2.0:
                self.scan_row = 0
            new_tilt = np.clip(
                self.center_tilt - self.scan_row * cfg.scan_row_step_deg,
                *cfg.tilt_limits,
            )
            self.cam.set_pose(new_pan, new_tilt)
        return self.state