import csv
import math
import time

import cv2

from .config import Config
from .controller import CoarseController
from .disturbances import Disturbances
from .metrics import Metrics
from .scene import SkyScene
from .sources import VirtualSource, WebcamSource
from . import ui
from .camera_model import VirtualCamera
from .vision import BlobDetector, KalmanTracker


def make_parser():
    import argparse

    p = argparse.ArgumentParser(
        description="AI-based virtual camera tracking system for coarse alignment "
                    "of mobile FSOC terminals (SIH 2026 / ISRO PS 26169)"
    )
    p.add_argument("--mode", choices=["virtual", "webcam"], default="virtual", help="frame source")
    p.add_argument("--width", type=int, default=800)
    p.add_argument("--height", type=int, default=600)
    p.add_argument("--fov", type=float, default=20.0, help="horizontal camera FOV in degrees")
    p.add_argument("--pan", type=float, default=0.0)
    p.add_argument("--tilt", type=float, default=6.0)
    p.add_argument("--trajectory", choices=["lissajous", "circle", "line", "stationary"],
                   default="lissajous", help="beacon motion type")
    p.add_argument("--traj-center-az", type=float, default=18.0)
    p.add_argument("--traj-center-el", type=float, default=8.0)
    p.add_argument("--traj-amp-az", type=float, default=7.0)
    p.add_argument("--traj-amp-el", type=float, default=5.0)
    p.add_argument("--traj-freq-az", type=float, default=0.05)
    p.add_argument("--traj-freq-el", type=float, default=0.033)
    p.add_argument("--traj-speed", type=float, default=1.0)
    p.add_argument("--noise", type=float, default=0.02, help="sensor noise sigma (fraction of 255)")
    p.add_argument("--turbulence", type=float, default=2.5, help="atmospheric turbulence in pixels")
    p.add_argument("--blur", type=int, default=3, help="sensor blur kernel size (0 to disable)")
    p.add_argument("--jitter", type=float, default=0.05, help="gimbal vibration in degrees")
    p.add_argument("--kp", type=float, default=4.0)
    p.add_argument("--ki", type=float, default=0.03)
    p.add_argument("--kd", type=float, default=0.6)
    p.add_argument("--max-rate", type=float, default=6.0, help="max slew rate deg/s")
    p.add_argument("--scan-window", type=float, default=34.0, help="acquisition scan width deg")
    p.add_argument("--lock-threshold", type=float, default=0.6, help="lock threshold in degrees")
    p.add_argument("--lock-frames", type=int, default=15)
    p.add_argument("--max-lost", type=int, default=20)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--autotrack", action="store_true", default=True,
                   help="enable automatic coarse alignment (PID)")
    p.add_argument("--no-autotrack", dest="autotrack", action="store_false")
    p.add_argument("--disturbances", action="store_true", default=True,
                   help="enable disturbance simulation")
    p.add_argument("--no-disturbances", dest="disturbances", action="store_false")
    p.add_argument("--hud", action="store_true", default=True)
    p.add_argument("--no-hud", dest="hud", action="store_false")
    p.add_argument("--horizon", type=float, default=-14.0)
    p.add_argument("--sun", action="store_true", help="render a bright sun in the scene")
    p.add_argument("--stars", type=int, default=1400)
    p.add_argument("--record", default="", help="record output video to path (mp4/avi)")
    p.add_argument("--log", default="", help="append frame metrics to CSV path")
    p.add_argument("--camera", type=int, default=0, help="webcam index")
    p.add_argument("--headless", action="store_true", help="run without a window")
    p.add_argument("--selftest", action="store_true", help="run N frames headless and print summary")
    p.add_argument("--frames", type=int, default=320, help="frames for selftest")
    return p


def build(cfg):
    scene = SkyScene(cfg)
    camera = VirtualCamera(cfg.width, cfg.height, cfg.fov_h_deg, cfg.pan_deg,
                           cfg.tilt_deg, cfg.pan_limits, cfg.tilt_limits)
    disturbances = Disturbances(cfg)
    if cfg.mode == "virtual":
        source = VirtualSource(scene, camera, disturbances, cfg)
    else:
        source = WebcamSource(cfg).set_disturbances(disturbances)
    return scene, camera, disturbances, source


def run(cfg, headless=False, max_frames=None):
    scene, camera, disturbances, source = build(cfg)
    det = BlobDetector()
    tracker = KalmanTracker(cfg.width, cfg.height, max_lost=cfg.max_lost)
    controller = CoarseController(cfg, camera)
    metrics = Metrics(cfg)
    headless = headless or cfg.headless
    autotrack = cfg.autotrack
    show_hud = cfg.show_hud
    writer = None
    log = None

    if cfg.record:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v") if cfg.record.lower().endswith("mp4") \
            else cv2.VideoWriter_fourcc(*"MJPG")
        writer = cv2.VideoWriter(cfg.record, fourcc, 60.0, (cfg.width, cfg.height))
    if cfg.log:
        log = open(cfg.log, "w", newline="")
        log_writer = csv.writer(log)
        log_writer.writerow(["t", "pan", "tilt", "err_deg", "meas_deg", "state", "det", "fps"])

    sim_t = 0.0
    frames = 0
    paused = False
    last_wall = time.perf_counter()
    quit_requested = False

    print("FSOC virtual camera coarse-alignment tracker")
    print("keys: [a] autotrack  [d] disturbances  [r] recenter/reacquire")
    print("      [p] pause  [h] hud  [q]/[ESC] quit  arrows = manual pan/tilt")
    print("mode=%s  target=%s  FOV=%.1fdeg  noise=%.3f turb=%.1fpx jitter=%.3fdeg"
          % (cfg.mode, cfg.trajectory, cfg.fov_h_deg, cfg.noise, cfg.turbulence_px, cfg.jitter_deg))

    while not quit_requested:
        loop0 = time.perf_counter()
        wall = time.perf_counter()
        fps = min(1.0 / max(wall - last_wall, 1e-6), 500.0)
        last_wall = wall
        metrics.set_fps(fps)

        if not paused:
            sim_t += cfg.sim_dt
        if max_frames is not None and frames >= max_frames:
            break

        frame, gt = source.step(sim_t)
        t0 = time.perf_counter()
        raw = det.detect(frame)
        smoothed = tracker.step(raw)
        vision_ms = (time.perf_counter() - t0) * 1000.0

        state = controller.step(smoothed, cfg.sim_dt, autotrack)
        frame_ms = (time.perf_counter() - loop0) * 1000.0

        metrics.update(sim_t, gt, camera, smoothed, raw, vision_ms, frame_ms, state)
        if log and gt is not None:
            log_writer.writerow([round(sim_t, 4), round(camera.pan, 4), round(camera.tilt, 4),
                                 round(metrics.last_err(), 4) if metrics.last_err() is not None else "",
                                 round(metrics.err_meas_deg[-1], 4) if metrics.err_meas_deg and metrics.err_meas_deg[-1] is not None else "",
                                 state, 1 if raw is not None else 0, round(metrics.fps, 2)])

        if not headless:
            out = ui.draw(frame, cfg, camera, metrics, controller, smoothed, raw, show_hud)
            if writer is not None:
                writer.write(out)
            cv2.imshow("FSOC Coarse Tracker", out)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                quit_requested = True
            elif key == ord("a"):
                autotrack = not autotrack
                print("autotrack:", autotrack)
            elif key == ord("d"):
                cfg.disturbances = not cfg.disturbances
                print("disturbances:", cfg.disturbances)
            elif key == ord("h"):
                show_hud = not show_hud
            elif key == ord("p"):
                paused = not paused
            elif key == ord("r"):
                camera.set_pose(cfg.pan_deg, cfg.tilt_deg)
                tracker.reset()
                controller.reset(cfg.pan_deg, cfg.tilt_deg)
            elif not autotrack:
                man = 3.0 * cfg.sim_dt
                if key == 81:
                    camera.set_pose(camera.pan - man, camera.tilt)
                elif key == 83:
                    camera.set_pose(camera.pan + man, camera.tilt)
                elif key == 82:
                    camera.set_pose(camera.pan, camera.tilt + man)
                elif key == 84:
                    camera.set_pose(camera.pan, camera.tilt - man)
        frames += 1

    summary = metrics.summary()
    if writer is not None:
        writer.release()
    if log is not None:
        log.close()
    if cfg.mode == "webcam":
        source.release()
    return summary


def main(argv=None):
    args = make_parser().parse_args(argv)
    if args.selftest:
        cfg = Config(
            mode=args.mode, width=400, height=300, fov_h_deg=args.fov,
            trajectory=args.trajectory, disturbances=args.disturbances,
            autotrack=args.autotrack, noise=args.noise, turbulence_px=args.turbulence,
            jitter_deg=args.jitter, seed=args.seed, headless=True, show_hud=False,
            pan_deg=args.pan, tilt_deg=args.tilt, lock_threshold_deg=args.lock_threshold,
        )
        summary = run(cfg, headless=True, max_frames=args.frames)
        for k, v in summary.items():
            print("%s: %s" % (k, v))
        ok = summary["locked"] and summary["mean_err_deg"] is not None and summary["mean_err_deg"] < 1.0
        print("SELFTEST PASS" if ok else "SELFTEST FAIL")
        return 0 if ok else 1

    cfg = Config(**{
        "mode": args.mode, "width": args.width, "height": args.height,
        "fov_h_deg": args.fov, "pan_deg": args.pan, "tilt_deg": args.tilt,
        "trajectory": args.trajectory, "traj_center_az": args.traj_center_az,
        "traj_center_el": args.traj_center_el, "traj_amp_az": args.traj_amp_az,
        "traj_amp_el": args.traj_amp_el, "traj_freq_az": args.traj_freq_az,
        "traj_freq_el": args.traj_freq_el, "traj_speed": args.traj_speed,
        "noise": args.noise, "turbulence_px": args.turbulence, "blur": args.blur,
        "jitter_deg": args.jitter, "kp": args.kp, "ki": args.ki, "kd": args.kd,
        "max_rate_deg_s": args.max_rate, "scan_window_deg": args.scan_window,
        "lock_threshold_deg": args.lock_threshold, "lock_frames": args.lock_frames,
        "max_lost": args.max_lost, "seed": args.seed, "autotrack": args.autotrack,
        "disturbances": args.disturbances, "show_hud": args.hud,
        "horizon_deg": args.horizon, "sun": args.sun, "num_stars": args.stars,
        "record": args.record, "log": args.log, "camera_index": args.camera,
        "headless": args.headless,
    })
    run(cfg)
    return 0