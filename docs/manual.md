<div class="cover">

<p class="kicker">SIH 2026 &middot; Indian Space Research Organisation &middot; Problem Statement 26169 &middot; Software</p>
<p class="cover-title">FSOC COARSE TRACKER</p>
<p class="cover-sub">AI-Based Virtual Camera Tracking System for Coarse Alignment of Mobile Free Space Optical Communication (FSOC) Terminals</p>
<p class="meta">User &amp; Developer Manual &middot; Version 0.1.0 &middot; September 2026</p>

</div>

[TOC]

# 1. Introduction

## 1.1 Problem context

Free Space Optical Communication (FSOC) offers gigabit-to-terabit data rates for next-generation
mobile networks, but deploying FSOC links between mobile platforms (satellites, UAVs, ground
stations) requires **Pointing, Acquisition and Tracking (PAT)** of very narrow laser beams. PAT
happens in two stages:

1. **Coarse alignment** - the transmitting terminal must locate the remote terminal and keep it
   inside its camera Field-of-View (FOV), and
2. **Fine alignment** - fine pointing optimisation of the beam.

Developing and testing these algorithms on real hardware is expensive. This project is the SIH 2026
submission for ISRO Problem Statement **26169**: *"Development of an AI-Based Virtual Camera Tracking
System for Coarse Alignment of Mobile Free Space Optical Communication (FSOC) Terminals"* - a purely
software platform that simulates the coarse-alignment loop using a *virtual* camera, a *virtual*
scene, and moving optical beacons.

## 1.2 What the system does

The system renders a synthetic night-sky scene containing a moving optical beacon, projects it
through a virtual pan/tilt camera with configurable FOV, then runs the full coarse-alignment loop:

observe &rarr; detect the beacon &rarr; estimate its position &rarr; steer the virtual gimbal to keep it centred.

The same detection/tracking pipeline runs against a **real USB webcam**, so the algorithm developed
here can be validated on both simulated and physical cues without special hardware.

## 1.3 Key capabilities

- Configurable virtual environment (scene, camera, beacon, trajectory)
- Moving beacons with selectable motion (lissajous, circle, line, stationary)
- Movable virtual camera with pan/tilt and FOV control (manual or automatic)
- Automatic acquisition - beacon is located without manual pointing (raster scan)
- Continuous tracking with Kalman filtering and a PID + velocity-feedforward controller
- Disturbance simulation (sensor noise, atmospheric turbulence, gimbal vibration, blur)
- Real-time statistics (pointing error, lock state, detection rate, FPS, latency)
- Webcam mode for physical-beacon experiments
- Video recording and CSV metrics export for post-analysis and BI tools (e.g. Tableau)

# 2. Getting started

## 2.1 Prerequisites

| Requirement | Version | Notes |
| --- | --- | --- |
| Python | 3.10+ | Developed and tested on Python 3.14 |
| numpy | &ge; 1.26 | Numerical arrays / rendering |
| opencv-python | &ge; 4.9 | Image processing, windows, Kalman filter |
| Display (interactive) | any X11 / Wayland | Only needed for the GUI window; fully headless otherwise |

## 2.2 Installation

```bash
cd ~/Projects/fsoc-tracker
python -m venv venv                 # if not already created
source venv/bin/activate
pip install -r requirements-fscam.txt
```

## 2.3 Sanity check

Run the headless regression test. It renders 320 frames, verifies that coarse alignment
locks the beacon, prints a metrics summary, and returns exit code 0/1.

```bash
python run_virtual_camera.py --selftest --frames 900
```

Expected tail of output (values vary with seed):

```text
frames: 900
fps: 97.5
vision_ms: 0.55
frame_ms: 10.41
detection_rate_pct: 75.7
locked: True
mean_err_deg: 0.588
peak_err_deg: 17.948
last_err_deg: 0.322
SELFTEST PASS
```

## 2.4 First interactive run

```bash
python run_virtual_camera.py
```

A window opens showing the simulated night sky. A reddish beacon appears in the scene; the
system first **SCANNING** (orange reticle, sweeping the gimbal), then acquires the beacon and
centres it. The HUD turns green and reports **LOCKED** once the pointing error stays below
the lock threshold long enough.

## 2.5 Interactive controls

| Key | Action |
| --- | --- |
| `a` | Toggle automatic coarse alignment (on/off) |
| `d` | Toggle disturbance simulation (on/off) |
| `p` | Pause / resume simulation time |
| `h` | Toggle the HUD overlay |
| `r` | Recentre camera and re-initiate acquisition (reset) |
| `Esc` / `q` | Quit |
| Arrow keys | Manual pan/tilt (only while autotrack is **off**) |

# 3. Operator guide

## 3.1 Operation modes

| Mode | Purpose | Ground truth |
| --- | --- | --- |
| `virtual` (default) | Full simulation: synthetic scene, beacon trajectory, all disturbances | Available (true beacon position is known), enabling exact pointing-error measurement and lock logic |
| `webcam` | Physical experiment: detect and track a bright optical beacon (LED/light source) seen by a USB camera | Unavailable; lock falls back to pixel (off-boresight) error |

```bash
python run_virtual_camera.py --mode virtual
python run_virtual_camera.py --mode webcam --camera 0 --width 640 --height 480
```

In webcam mode the trajectory, vibration and pixel-turbulence models do not apply; sensor noise
and blur may still be enabled to stress the detector.

## 3.2 CLI options reference

### 3.2.1 General

| Option | Default | Description |
| --- | --- | --- |
| `--mode {virtual,webcam}` | `virtual` | Frame source |
| `--width` | `800` | Viewport width (px) |
| `--height` | `600` | Viewport height (px) |
| `--fov` | `20.0` | Horizontal FOV (deg) |
| `--pan` | `0.0` | Initial pan (deg) |
| `--tilt` | `6.0` | Initial tilt (deg) |
| `--seed` | `42` | RNG seed (reproducible scenes) |
| `--headless` | off | Run without a window (useful for automation) |
| `--hud` / `--no-hud` | on | Toggle HUD overlay |

### 3.2.2 Beacon trajectory

| Option | Default | Description |
| --- | --- | --- |
| `--trajectory {lissajous,circle,line,stationary}` | `lissajous` | Beacon motion model |
| `--traj-center-az` | `18.0` | Trajectory centre, azimuth (deg) |
| `--traj-center-el` | `8.0` | Trajectory centre, elevation (deg) |
| `--traj-amp-az` | `7.0` | Azimuth amplitude (deg) |
| `--traj-amp-el` | `5.0` | Elevation amplitude (deg) |
| `--traj-freq-az` | `0.05` | Azimuth oscillation frequency (Hz) |
| `--traj-freq-el` | `0.033` | Elevation oscillation frequency (Hz) |
| `--traj-speed` | `1.0` | Time-scale multiplier |

### 3.2.3 Disturbances

| Option | Default | Description |
| --- | --- | --- |
| `--disturbances` / `--no-disturbances` | on | Master switch for disturbance simulation |
| `--noise` | `0.02` | Sensor noise sigma (fraction of 255) |
| `--turbulence` | `2.5` | Atmospheric turbulence: pixel wander magnitude |
| `--blur` | `3` | Sensor blur kernel size (0 = off) |
| `--jitter` | `0.05` | Gimbal vibration amplitude (deg) |

### 3.2.4 Coarse-alignment control

| Option | Default | Description |
| --- | --- | --- |
| `--autotrack` / `--no-autotrack` | on | Enable PID tracking |
| `--kp` | `4.0` | Proportional gain |
| `--ki` | `0.03` | Integral gain |
| `--kd` | `0.6` | Derivative gain |
| `--max-rate` | `6.0` | Maximum gimbal slew rate (deg/s) |
| `--scan-window` | `34.0` | Acquisition raster-scan width (deg) |
| `--lock-threshold` | `0.6` | Pointing-error threshold for lock (deg) |
| `--lock-frames` | `15` | Consecutive frames below threshold to declare lock |
| `--max-lost` | `20` | Frames without detection before re-acquisition |

### 3.2.5 Scene and output

| Option | Default | Description |
| --- | --- | --- |
| `--horizon` | `-14.0` | Horizon elevation in the scene (deg) |
| `--sun` | off | Render a bright sun disk in the scene |
| `--stars` | `1400` | Number of background stars |
| `--record` | (none) | Record processed video (`.mp4` or `.avi`) |
| `--log` | (none) | Append per-frame metrics to CSV |
| `--camera` | `0` | Webcam index (webcam mode) |
| `--selftest` | off | Run headless regression test and exit |
| `--frames` | `320` | Number of frames to run for `--selftest` |

## 3.3 Example runs

Acquire and track the default moving beacon:

```bash
python run_virtual_camera.py --trajectory lissajous
```

Stress test with heavy disturbances:

```bash
python run_virtual_camera.py --noise 0.08 --turbulence 8 --jitter 0.3
```

Track a slow circular target with a brighter, wider FOV:

```bash
python run_virtual_camera.py --trajectory circle --traj-freq-az 0.03 --fov 30 \
    --traj-amp-az 4 --traj-amp-el 4
```

Live experiment with a USB camera (point an LED at the lens):

```bash
python run_virtual_camera.py --mode webcam --camera 0 --record demo.mp4 --log data/manual_run.csv
```

Open-loop demonstration (no autotrack; control the gimbal yourself with arrow keys):

```bash
python run_virtual_camera.py --no-autotrack
```

## 3.4 Understanding the HUD

| HUD element | Meaning |
| --- | --- |
| State (SCANNING / TRACKING / LOCKED / MANUAL) | Acquisition & lock state of the controller |
| `FPS  Frame ms  Vision ms` | Loop performance: frames/s, full-loop time, perception latency |
| `Detections %` | Fraction of frames where the detector found the beacon |
| `PAN / TILT` | Current commanded gimbal angles |
| `FOV` | Horizontal field of view |
| `Pointing err deg` | True angular error between boresight and beacon (virtual mode) |
| `Measured off-boresight deg` | Angular error computed from the detected centroid (both modes) |
| Green sparkline | Rolling history of the pointing error |
| Cross-hair moving reticle | Filtered beacon position (green = locked, yellow = tracking) |
| Orange reticle + `ACQUIRING...` | Raster-scan search in progress |

# 4. Outputs and metrics

## 4.1 Metrics definitions

| Metric | Definition |
| --- | --- |
| Pointing error (`err_deg`) | `angular_sep(pan, tilt, beacon_az, beacon_el)` - true geodesic angle between commanded boresight and the real beacon direction. Only available in virtual mode (ground truth is known). |
| Measured error (`meas_deg`) | Angular offset of the Kalman-filtered detection centroid from the image centre: `atan2(distance_px, focal_px)`. Available in both modes. |
| Lock | `err_deg` (virtual) or `meas_deg` (webcam) below `--lock-threshold` for `--lock-frames` consecutive frames. |
| Detection rate | Fraction of frames with a raw blob detection. |
| FPS / frame time | Exponential moving average of loop frequency and duration. |
| Vision latency | EMA of detector runtime (ms) - a proxy for perception pipeline latency. |

## 4.2 CSV log format

Produced by `--log path.csv`; one row per frame:

```text
t,pan,tilt,err_deg,meas_deg,state,det,fps
```

| Column | Type | Description |
| --- | --- | --- |
| `t` | float | Simulation time (s) |
| `pan`, `tilt` | float | Commanded gimbal angles (deg) |
| `err_deg` | float (blank if unavailable) | True pointing error (deg) |
| `meas_deg` | float (blank if blank) | Measured off-boresight error (deg) |
| `state` | str | `SEARCH`, `TRACK` (or `LOST`) |
| `det` | int 0/1 | Whether a raw detection existed this frame |
| `fps` | float | Loop rate for this frame |

Example:

```text
t,pan,tilt,err_deg,meas_deg,state,det,fps
0.016,0.064,6.0,17.9485,,SEARCH,0,177.1
0.032,0.128,6.0,17.9216,,SEARCH,0,168.2
...
3.504,13.59,6.80,0.412,0.419,TRACK,1,96.3
```

## 4.3 Video recording

`--record out.mp4` (or `.avi`) writes the processed frames (HUD included) at 60 fps.

## 4.4 Selftest report

`--selftest` prints a machine-readable summary used by CI/regression checks:

| Key | Description |
| --- | --- |
| `frames` | Frames simulated |
| `fps`, `vision_ms`, `frame_ms` | Performance |
| `detection_rate_pct` | Detector success rate |
| `locked` | Whether the coarse-alignment loop reached lock |
| `mean_err_deg` | Mean true pointing error over the run |
| `peak_err_deg` | Worst-case pointing error |
| `last_err_deg` | Final pointing error |

# 5. Architecture

## 5.1 Overall data flow

```text
┌────────────────────────── Scene & trajectory ──────────────────────────┐
│ SkyScene (stars, horizon, sun)   beacon(t) -> (az, el)                 │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
        vibration (gimbal jitter)  ▼  turbulence (pixel wander)        noise+blur
┌────── VirtualCamera ──────┐   render       ┌──────── Sensor ─────────┐
│ pan/tilt/FOV, pinhole     │ ─────────────► │ disturbance.apply(frame)│
│ project_world(), rendering│                 └───────────┬────────────┘
└───────────────────────────┘                             │ frame
                                                          ▼
                                          ┌──────── Perception ─────────┐
                                          │ BlobDetector -> KalmanTracker│
                                          └───────────┬────────────────┘
                                                      │ filtered centroid (u,v)
                                                      ▼
                                          ┌──────── Controller ─────────┐
                                          │ SEARCH scan / PID + feedforward │
                                          └───────────┬────────────────┘
                                                      │ dpan/dt, dtilt/dt
                                                      ▼
                                          pan/tilt update ──► loop back to camera
                                                      │
                                                      ▼
                                          ┌──────── Metrics + HUD ──────┐
                                          │ error, lock, FPS, CSV, video │
                                          └──────────────────────────────┘
```

In `webcam` mode the left half (renderer/simulation) is replaced by a real camera frame; the
perception, controller and metrics pipeline is identical.

## 5.2 Module reference

| Module | File | Responsibility |
| --- | --- | --- |
| `Config` | `fscam/config.py` | Single dataclass with every tunable parameter |
| `SkyScene` | `fscam/scene.py` | Star field, horizon, optional sun, beacon trajectory factory |
| `VirtualCamera` | `fscam/camera_model.py` | Pinhole projection, pan/tilt pose, FOV, pixel &harr; angle conversions |
| `renderer` | `fscam/renderer.py` | Draws the scene into the camera frame (background, stars, beacon bloom) |
| `Disturbances` | `fscam/disturbances.py` | Vibration (OU), turbulence (OU), sensor noise, blur |
| `BlobDetector` / `KalmanTracker` | `fscam/vision.py` | Bright-blob perception; constant-velocity Kalman filtering with gating |
| `CoarseController` | `fscam/controller.py` | SEARCH/TRACK/LOST state machine; raster scan; PID + feedforward |
| `Metrics` | `fscam/metrics.py` | Error histories, lock detection, FPS/latency EMAs, summaries |
| `ui` | `fscam/ui.py` | HUD overlay, reticles, sparkline |
| `VirtualSource` / `WebcamSource` | `fscam/sources.py` | Frame producers (simulation or camera) |
| `app` | `fscam/app.py` | Main loop, CLI parsing, keyboard handling, recording, CSV |
| entry point | `run_virtual_camera.py` | Thin launcher for `fscam.app.main` |

## 5.3 Coordinate and projection model

The camera poses uses a right-handed frame with axes:

- **forward** `w` = direction of boresight at (pan, tilt)
- **right** `r` (horizontal)
- **up** `u` (perpendicular)

A target direction `d` is expressed in camera coordinates as:

```text
az_c = atan2(d . r, d . w)        # positive = right of centre
el_c = atan2(d . u, d . w)        # positive = above centre
```

Pixels follow a gnomonic (pinhole) projection using the focal length derived from the horizontal FOV:

```text
f_px   = (W / 2) / tan(FOV_h / 2)
u      = W / 2 + f_px * tan(az_c)
v      = H / 2 - f_px * tan(el_c)
```

`WorldCamera.pixel_to_angles()` inverts this to map a detection back to the angular domain used by
the controller, which makes the control law resolution-independent.

## 5.4 Detection and tracking

**BlobDetector** thresholds the grayscale image relative to its brightest pixels, cleanly separates
components, keeps compact bright blobs (area between 4 and 900 px, minimum mean score), and returns
an **intensity-weighted subpixel centroid** for the best candidate.

**KalmanTracker** implements a constant-velocity Kalman filter over `(u, v, du, dv)`:

- predicts each frame (bridges the inter-frame gap and provides graceful occlusion handling),
- corrects detections inside a Mahalanobis-like pixel gate (rejects outliers),
- increments a `lost` counter on missing detections and returns `None` after `--max-lost` frames so
  the controller can re-acquire.

Gating plus the intensity-weighted centroid keeps the filter stable against star-like distractors.

## 5.5 Coarse-alignment controller

A state machine drives the virtual gimbal:

- **SEARCH (acquisition):** raster-scan pan/tilt across `--scan-window` until a beacon is
  detected. This fulfils the "locate the remote terminal without manual pointing" requirement.
- **TRACK:** PID on the angular error plus a **velocity feedforward** term. The feedforward
  estimates beacon angular velocity from the filtered centroid history, which removes most of the
  steady-state lag. The combined command is clamped to `--max-rate`.
- **LOST:** after `--max-lost` frames without a filtered detection, returns to SEARCH.

The feedforward is important: with proportional control alone the steady-state error tends toward
`target_slew / Kp` (e.g. a beacon slewing 4.8&deg;/s against Kp=3 leaves about 1.6&deg; of bias).

## 5.6 Disturbance models

| Disturbance | Model | Config |
| --- | --- | --- |
| Gimbal vibration | Ornstein-Uhlenbeck process added to camera pan/tilt at render time | `--jitter` |
| Atmospheric turbulence | OU process shifting the beacon pixel centre, plus a Gaussian blur at the sensor | `--turbulence`, `--blur` |
| Sensor noise | Zero-mean Gaussian with std = `--noise` x 255 added to the frame | `--noise` |

Enabling/disabling all of them at runtime with the `d` key lets a judge observe tracking degraded
and recovered live.

## 5.7 Metrics implementation

`Metrics` maintains rolling deques of the true and measured errors (for the sparkline and CSV),
a peak tracker, a lock frame counter, and EMA performance timers. Pointing error uses the true scene
beacon azimuth/elevation against the *commanded* gimbal pose, decoupled from detection so that
controller quality and perception quality are reported separately.

# 6. Tuning and performance

## 6.1 PID gains and feedforward

- `--kp` dominates residual error; aggressive values can oscillate near target turn-around.
- `--kd` dampens overshoot on fast changes; keep small (0.5-1.0).
- `--ki` removes small long-term bias; keep small to avoid wind-up (`--max-rate` limits slew).
- The feedforward term is tuned by `_ff_alpha` in `fscam/controller.py`. Raise it for faster
  slew-accurate tracking, lower it for smoother estimates.
- `--max-rate` should exceed the peak beacon angular rate, or tracking will saturate.

## 6.2 Acquisition / scan

- `--scan-window` sets the uncertainty region to sweep during acquisition. It should cover the
  expected beacon region (the wide default of 34&deg; comfortably spans the default trajectory).
- `--scan-speed` and `--scan-row-step` (code defaults 4&deg;/s, 2.5&deg;) trade acquisition time
  against sweep coverage.

## 6.3 Disturbance stress levels

| `--noise` | `--turbulence` | `--jitter` | Effect |
| --- | --- | --- | --- |
| 0.02 | 2.5 | 0.05 | Nominal (default) |
| 0.05 | 8 | 0.3 | Pronounced scintillation & vibration; tracking still holds |
| 0.10+ | 12+ | 0.5+ | Near-visibility limit; demonstrates robust filter behaviour |

## 6.4 Rendering and FPS

- Default 800x600 renders comfortably above 90 fps on a desktop.
- Lower `--width`/`--height` and `--stars` for weak hardware.
- The `--selftest` path uses 400x300 for fast regression runs.

## 6.5 Regression testing with selftest

`--selftest` is deterministic for a fixed `--seed`. Use it as the automated gate (CI) after any
code change: it asserts the loop can lock and that mean error stays low.

# 7. SIH requirements traceability matrix

| ISRO functional requirement | Implementation | How to demonstrate |
| --- | --- | --- |
| Configurable virtual environment | `Config`, `scene.py`, `renderer.py`, `camera_model.py` | Change scene/target/camera via CLI flags and reload |
| Moving targets (one or more beacons) | `make_trajectory` in `scene.py` (lissajous/circle/line/stationary) | Run `--trajectory circle` and watch the beacon sweep |
| Movable virtual camera | pan/tilt in `camera_model.py`, `controller.py`, arrow keys | Toggle `--no-autotrack` and steer with arrow keys |
| Automatic detection | `BlobDetector` + SEARCH scan in `controller.py` | Start off-target; observe `ACQUIRING...` until found |
| Continuous tracking | `KalmanTracker` + PID/feedforward | Confirm HUD reads `LOCKED` while the beacon moves |
| Disturbances (noise, turbulence, vibration, camera movement) | `disturbances.py` | Press `d`; watch error rise and recover when re-enabled |
| Real-time statistics | `metrics.py`, `ui.py` | Read error/lock/FPS/latency on the HUD and in the CSV log |
| Software-only, no special hardware | whole project (virtual + webcam modes) | Run anywhere with Python + OpenCV |

# 8. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `RuntimeError: Cannot open camera index 0` | The webcam is busy or absent. Try `--camera 1`; list devices with `ls /dev/video*`. |
| GUI does not open in interactive mode | Run under a desktop session, or use `--headless`/`--selftest` (fully deterministic). |
| `QFontDatabase: Cannot find font directory ... cv2/qt/fonts` | Cosmetic OpenCV-Qt warning; safe to ignore. |
| Slow frame rate | Reduce `--width/--height` and `--stars`; disable `--no-hud` while developing. |
| `SELFTEST FAIL` | Regression in tracking; check `mean_err_deg`, `fps`, and recent module changes. The test is deterministic for a fixed seed. |
| Beacon never acquired | `--scan-window` too small for the trajectory region; increase it or move `--traj-center-*`. |
| Tracking lags the target | Increase `--max-rate` above beacon slew, or raise feedforward `_ff_alpha` in `controller.py`. |

# 9. Extension guide

## 9.1 New beacon trajectories

`scene.py: make_trajectory(cfg)` returns `traj(t) -> (az, el)`. Add a branch in the `kind` dispatch
for a new name and it becomes available via `--trajectory`. Trajectories are pure functions of time,
so any parametrisation is supported.

## 9.2 Learned (AI) detector

The perception stage (`vision.BlobDetector.detect`) is a small, drop-in interface:

```text
detect(frame) -> (u, v, score, area) | None
```

Swap the classical threshold+blob logic for a learned model (e.g. YOLO, a small CNN trained on
rendered frames, or a transformer tracker) while keeping `KalmanTracker`, the controller and the
metrics untouched. This is the natural path to strengthening the "AI-based" claim beyond the
statistical baseline.

## 9.3 Multi-beacon support

- Renderer: extend `SkyScene` to hold a list of beacons.
- Perception: return a list of candidates from `BlobDetector` and run one `KalmanTracker` per ID.
- Controller/metrics: extend the lock logic per beacon, and add a beacon-ID column to the CSV.

## 9.4 Data export for analytics

The CSV (`--log`) is directly consumable by Tableau, Excel, or pandas. Suggested Tableau dashboard:
- Line chart of `err_deg` and `meas_deg` over `t`, partitioned by `state`
- Histogram of `err_deg` while `state=TRACK` to show steady-state distribution
- Scatter `pan` vs `tilt` to visualise the gimbal path during acquisition
- KPI tiles for lock duration, detection rate, mean/peak error

See Section 10 for a full field reference.

# 10. Appendix

## 10.1 Configuration reference (`fscam/config.py`)

| Field | Default | CLI flag | Description |
| --- | --- | --- | --- |
| `mode` | `virtual` | `--mode` | Frame source |
| `width` / `height` | `800` / `600` | `--width` / `--height` | Viewport size (px) |
| `fov_h_deg` | `20.0` | `--fov` | Horizontal FOV (deg) |
| `pan_deg` / `tilt_deg` | `0.0` / `6.0` | `--pan` / `--tilt` | Initial pose |
| `pan_limits` / `tilt_limits` | `(-90,90)` / `(-30,30)` | (config-only) | Gimbal travel limits |
| `trajectory` | `lissajous` | `--trajectory` | Beacon motion |
| `traj_center_az` / `traj_center_el` | `18.0` / `8.0` | `--traj-center-*` | Trajectory centre |
| `traj_amp_az` / `traj_amp_el` | `7.0` / `5.0` | `--traj-amp-*` | Amplitudes |
| `traj_freq_az` / `traj_freq_el` | `0.05` / `0.033` | `--traj-freq-*` | Frequencies (Hz) |
| `traj_speed` | `1.0` | `--traj-speed` | Time multiplier |
| `horizon_deg` | `-14.0` | `--horizon` | Scene horizon |
| `num_stars` | `1400` | `--stars` | Star-field size |
| `seed` | `42` | `--seed` | RNG seed |
| `beacon_sigma_px` | `1.8` | (config-only) | Beacon point-spread radius |
| `sun` | `False` | `--sun` | Render sun disk |
| `noise` | `0.02` | `--noise` | Sensor noise sigma |
| `turbulence_px` | `2.5` | `--turbulence` | Turbulence wander (px) |
| `blur` | `3` | `--blur` | Blur kernel (0=off) |
| `jitter_deg` | `0.05` | `--jitter` | Gimbal vibration (deg) |
| `kp` / `ki` / `kd` | `4.0` / `0.03` / `0.6` | `--kp/--ki/--kd` | PID gains |
| `max_rate_deg_s` | `6.0` | `--max-rate` | Slew limit (deg/s) |
| `scan_window_deg` | `34.0` | `--scan-window` | Acquisition scan width |
| `scan_speed_deg_s` | `4.0` | (config-only) | Scan sweep rate |
| `scan_row_step_deg` | `2.5` | (config-only) | Scan raster pitch |
| `lock_threshold_deg` | `0.6` | `--lock-threshold` | Lock error band |
| `lock_frames` | `15` | `--lock-frames` | Frames for lock |
| `max_lost` | `20` | `--max-lost` | Frames before re-acquisition |
| `autotrack` | `True` | `--autotrack/--no-autotrack` | Enable PID tracking |
| `disturbances` | `True` | `--disturbances/--no-disturbances` | Master disturbance switch |
| `show_hud` | `True` | `--hud/--no-hud` | HUD visibility |
| `record` | `""` | `--record` | Output video path |
| `log` | `""` | `--log` | Output CSV path |
| `camera_index` | `0` | `--camera` | Webcam index |
| `headless` | `False` | `--headless` | No-window mode |
| `sim_dt` | `0.016` | (config-only) | Simulation step (s) |

## 10.2 File layout

```text
fsoc-tracker/
├── fscam/
│   ├── __init__.py
│   ├── app.py            # CLI, main loop, key handling, recording/CSV
│   ├── camera_model.py   # pinhole projection, pan/tilt, FOV
│   ├── config.py         # Config dataclass
│   ├── controller.py     # SEARCH/TRACK/LOST, PID + feedforward
│   ├── disturbances.py   # vibration, turbulence, noise, blur
│   ├── metrics.py        # errors, lock, FPS, latency
│   ├── renderer.py       # scene -> frame rendering
│   ├── scene.py          # stars, trajectories, SkyScene
│   ├── sources.py        # Virtual/Webcam frame sources
│   ├── ui.py             # HUD overlay
│   └── vision.py         # BlobDetector, KalmanTracker
├── docs/
│   ├── manual.md         # this manual
│   ├── style.css         # PDF print stylesheet
│   ├── build_pdf.sh      # markdown -> PDF builder
│   └── manual.pdf        # generated PDF
├── run_virtual_camera.py # launcher
├── requirements-fscam.txt
└── venv/                 # Python environment
```

## 10.3 Quick CLI table

```text
python run_virtual_camera.py                          # interactive virtual demo
python run_virtual_camera.py --mode webcam            # USB webcam tracking
python run_virtual_camera.py --selftest --frames 900  # regression check (exit code)
python run_virtual_camera.py --trajectory circle      # different beacon motion
python run_virtual_camera.py --noise 0.08 --turbulence 8 --jitter 0.3  # stress test
python run_virtual_camera.py --record demo.mp4 --log data.csv           # capture
python run_virtual_camera.py --help                   # full option help
```