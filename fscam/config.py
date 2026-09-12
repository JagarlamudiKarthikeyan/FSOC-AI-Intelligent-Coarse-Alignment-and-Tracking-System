from dataclasses import dataclass


@dataclass
class Config:
    mode: str = "virtual"
    width: int = 800
    height: int = 600
    fov_h_deg: float = 20.0
    pan_deg: float = 0.0
    tilt_deg: float = 6.0
    pan_limits: tuple = (-90.0, 90.0)
    tilt_limits: tuple = (-30.0, 30.0)
    trajectory: str = "lissajous"
    traj_center_az: float = 18.0
    traj_center_el: float = 8.0
    traj_amp_az: float = 7.0
    traj_amp_el: float = 5.0
    traj_freq_az: float = 0.05
    traj_freq_el: float = 0.033
    traj_speed: float = 1.0
    horizon_deg: float = -14.0
    num_stars: int = 1400
    seed: int = 42
    beacon_sigma_px: float = 1.8
    sun: bool = False
    noise: float = 0.02
    turbulence_px: float = 2.5
    blur: int = 3
    jitter_deg: float = 0.05
    kp: float = 4.0
    ki: float = 0.03
    kd: float = 0.6
    max_rate_deg_s: float = 6.0
    scan_window_deg: float = 34.0
    scan_speed_deg_s: float = 4.0
    scan_row_step_deg: float = 2.5
    lock_threshold_deg: float = 0.6
    lock_frames: int = 15
    max_lost: int = 20
    autotrack: bool = True
    disturbances: bool = True
    show_hud: bool = True
    record: str = ""
    headless: bool = False
    camera_index: int = 0
    sim_dt: float = 0.016
    log: str = ""