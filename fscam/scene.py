import numpy as np


def make_stars(n, seed):
    rng = np.random.default_rng(seed)
    az = rng.uniform(0.0, 360.0, n)
    el = rng.uniform(0.0, 88.0, n)
    mag = rng.uniform(0.5, 8.0, n)
    return az, el, mag


def make_trajectory(cfg):
    kind = cfg.trajectory

    def traj(t):
        tt = t * cfg.traj_speed
        if kind == "stationary":
            return float(cfg.traj_center_az), float(cfg.traj_center_el)
        if kind == "circle":
            az = cfg.traj_center_az + cfg.traj_amp_az * np.cos(2.0 * np.pi * cfg.traj_freq_az * tt + np.pi / 2.0)
            el = cfg.traj_center_el + cfg.traj_amp_el * np.sin(2.0 * np.pi * cfg.traj_freq_az * tt)
        elif kind == "line":
            phase = (tt * cfg.traj_freq_az) % 1.0
            az = cfg.traj_center_az - cfg.traj_amp_az + 2.0 * cfg.traj_amp_az * phase
            el = cfg.traj_center_el
        else:
            az = cfg.traj_center_az + cfg.traj_amp_az * np.sin(2.0 * np.pi * cfg.traj_freq_az * tt)
            el = cfg.traj_center_el + cfg.traj_amp_el * np.sin(2.0 * np.pi * cfg.traj_freq_el * tt)
        return float(az), float(el)

    return traj


class SkyScene:
    def __init__(self, cfg):
        self.cfg = cfg
        self.horizon_deg = cfg.horizon_deg
        self.star_az, self.star_el, self.star_mag = make_stars(cfg.num_stars, cfg.seed)
        self.sun_enabled = cfg.sun
        self.sun_az = 60.0
        self.sun_el = 12.0
        self.traj = make_trajectory(cfg)

    def beacon(self, t):
        return self.traj(t)