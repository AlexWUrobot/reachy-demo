"""
ReachyChef Non-Verbal Sign System for Reachy Mini
Each sign is a standalone function — call them directly from an LLM orchestrator.

Usage:
    from reachy_mini_signs import ReachyChef

    with ReachyChef() as chef:
        chef.sign("good_job")
        chef.sign("stir")
        chef.behavior("victory_bow")
"""

import time
import math
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose


class ReachyChef:
    """Wrapper around ReachyMini exposing named cooking signs."""

    # All available signs — useful for LLM tool definitions
    SIGNS = [
        "start", "stop", "wait", "good_job", "warning", "error",
        "cut", "stir", "add_ingredient", "heat", "timer_done",
        "look_here", "check_pan", "danger",
    ]
    BEHAVIORS = [
        "sniff", "mirror_stir", "timeout_tilt", "victory_bow", "freeze_and_stare",
    ]

    def __init__(self):
        pass

    def __enter__(self):
        self._mini.__enter__()
        self._mini.wake_up()
        return self

    def __exit__(self, *args):
        self._mini.goto_sleep()
        self._mini.__exit__(*args)

    # ── Low-level helpers ────────────────────────────────────────────────────

    def _move(self, roll=0.0, pitch=0.0, yaw=0.0, duration=0.6):
        pose = create_head_pose(z=pitch, roll=roll, degrees=True, mm=True)
        self._mini.goto_target(
            head=pose,
            body_yaw=math.radians(yaw),
            duration=duration,
        )
        time.sleep(duration + 0.05)

    def _center(self, duration=0.4):
        self._move(0, 0, 0, duration)

    def _antenna(self, left=0.0, right=0.0, duration=0.4):
        self._mini.goto_target(antennas=[left, right], duration=duration)
        time.sleep(duration + 0.05)

    # ── Public dispatch ──────────────────────────────────────────────────────

    def sign(self, name: str, mini_instance,**kwargs):
        """Call a sign by name. Raises ValueError for unknown signs."""
        self._mini=mini_instance
        fn = getattr(self, f"_sign_{name}", None)
        if fn is None:
            raise ValueError(f"Unknown sign '{name}'. Available: {self.SIGNS}")
        if fn:
            fn(**kwargs)

    def behavior(self, name: str, mini_instance, **kwargs):
        """Call a signature behavior by name."""
        self._mini=mini_instance
        fn = getattr(self, f"_behavior_{name}", None)
        if fn is None:
            raise ValueError(f"Unknown behavior '{name}'. Available: {self.BEHAVIORS}")
        if fn:
            fn(**kwargs)

    # ── Core signs ───────────────────────────────────────────────────────────

    def _sign_start(self):
        self._antenna(0.6, 0.6, duration=0.3)
        self._move(pitch=-15, duration=0.5)
        self._move(pitch=-4,  duration=0.4)
        self._center()
        self._antenna(0, 0)

    def _sign_stop(self):
        # head up
        self._move(pitch=15, duration=0.8)
        # cross antennas into X
        self._mini.set_target_antenna_joint_positions([math.radians(60), math.radians(-60)])
        # hold still — the freeze
        time.sleep(2.0)
        # release back to normal
        self._mini.set_target_antenna_joint_positions([0, 0])
        self._center()

    def _sign_wait(self):
        # left = minute hand (faster), right = hour hand (slower)
        steps, duration = 100, 5.0
        for i in range(steps + 1):
            t = i / steps
            minute = math.radians(360 * t)
            hour   = math.radians(360 * t * 0.5)
            self._mini.set_target_antenna_joint_positions([minute, hour])
            time.sleep(duration / steps)
        time.sleep(0.5)
        # return to zero
        self._mini.set_target_antenna_joint_positions([0, 0])
        time.sleep(1.0)

    def _sign_good_job(self):
        self._antenna(1.0, 1.0, duration=0.2)
        for _ in range(2):
            self._move(pitch=-18, duration=0.25)
            self._move(pitch=4,   duration=0.25)
        self._move(roll=10,  duration=0.2)
        self._move(roll=-10, duration=0.2)
        self._move(roll=8,   duration=0.15)
        self._center()
        self._antenna(0, 0)

    def _sign_warning(self):
        self._antenna(0.4, -0.4, duration=0.3)
        self._move(yaw=-35, pitch=-4, duration=0.7)
        time.sleep(0.5)
        for _ in range(2):
            self._move(yaw=-44, duration=0.3)
            self._move(yaw=-26, duration=0.3)
        self._center()
        self._antenna(0, 0)

    def _sign_error(self):
        self._antenna(-0.4, -0.4, duration=0.3)
        for _ in range(3):
            self._move(yaw=22,  duration=0.35)
            self._move(yaw=-22, duration=0.35)
        self._center()
        self._antenna(0, 0)

    # ── Cooking actions ──────────────────────────────────────────────────────

    def _sign_cut(self):
        self._center(duration=0.3)
        # cross antennas slowly into X before chopping
        steps, duration = 40, 1.5
        for i in range(steps + 1):
            t = i / steps
            self._mini.set_target_antenna_joint_positions([
                math.radians(60 * t),
                math.radians(-60 * t),
            ])
            time.sleep(duration / steps)
        time.sleep(0.3)
        for _ in range(3):
            self._move(pitch=-22, duration=0.2)
            self._move(pitch=4,   duration=0.2)
        # release antennas
        self._mini.set_target_antenna_joint_positions([0, 0])
        self._center()

    def _sign_stir(self):
        steps, r_roll, r_pitch = 16, 12, 8
        dt = 1.8 / steps
        for _ in range(2):
            for i in range(steps):
                a = 2 * math.pi * i / steps
                self._move(
                    roll  =  r_roll  * math.sin(a),
                    pitch = -r_pitch * math.cos(a) + 3,
                    duration=dt,
                )
        self._center()

    def _sign_add_ingredient(self):
        # form L: right antenna up (90°), left antenna flat (0°)
        steps, duration = 60, 0.58
        for i in range(steps + 1):
            t = i / steps
            self._mini.set_target_antenna_joint_positions([
                math.radians(0),
                math.radians(90 * t),
            ])
            time.sleep(duration / steps)

        # slowly tilt left and return 3 times
        for _ in range(3):
            self._move(roll=-30, duration=1.2)
            self._move(roll=0,   duration=1.2)

        # return to normal
        self._mini.set_target_antenna_joint_positions([0, 0])
        self._center(duration=0.8)

    def _sign_heat(self, **_):
        cycles = 10
        for i in range(cycles):
            direction = 1 if i % 2 == 0 else -1
            pose = create_head_pose(z=-5, roll=0, degrees=True, mm=True)
            self._mini.goto_target(
                head=pose,
                body_yaw=math.radians(8 * direction),
                duration=0.15,
            )
            self._mini.set_target_antenna_joint_positions([
                math.radians(30 * direction),
                math.radians(-30 * direction),
            ])
            time.sleep(0.15)

            pose = create_head_pose(z=5, roll=0, degrees=True, mm=True)
            self._mini.goto_target(
                head=pose,
                body_yaw=math.radians(-8 * direction),
                duration=0.15,
            )
            self._mini.set_target_antenna_joint_positions([
                math.radians(-30 * direction),
                math.radians(30 * direction),
            ])
            time.sleep(0.15)

        self._mini.set_target_body_yaw(0)
        self._mini.set_target_antenna_joint_positions([0, 0])
        self._center(duration=0.5)

    def _sign_timer_done(self):
        for _ in range(2):
            self._antenna(1.0, -1.0, duration=0.15)
            self._antenna(-1.0, 1.0, duration=0.15)
        for _ in range(4):
            self._move(yaw=24,  duration=0.18)
            self._move(yaw=-24, duration=0.18)
        self._move(pitch=-14, yaw=-20, duration=0.4)
        time.sleep(0.5)
        self._center()
        self._antenna(0, 0)

    # ── Attention signals ────────────────────────────────────────────────────

    def _sign_look_here(self):
        # left antenna folded down, right antenna up
        self._mini.set_target_antenna_joint_positions([
            math.radians(-90),
            math.radians(90),
        ])
        time.sleep(0.8)

        # rotate body and wave right antenna 3 times
        for _ in range(3):
            self._mini.set_target_body_yaw(math.radians(10))
            self._mini.set_target_antenna_joint_positions([math.radians(-180), math.radians(-30)])
            time.sleep(0.5)
            self._mini.set_target_body_yaw(math.radians(-10))
            self._mini.set_target_antenna_joint_positions([math.radians(-180), math.radians(30)])
            time.sleep(0.5)

        # return to center
        self._mini.set_target_body_yaw(0)
        self._mini.set_target_antenna_joint_positions([0, 0])
        time.sleep(1.0)

    def _sign_check_pan(self):
        self._move(yaw=-25, pitch=-18, duration=0.6)
        time.sleep(0.5)
        for _ in range(2):
            self._move(yaw=-25, pitch=-26, duration=0.3)
            self._move(yaw=-25, pitch=-12, duration=0.3)
        self._center()

    def _sign_danger(self):
        self._antenna(-1.0, -1.0, duration=0.15)
        self._move(pitch=18, duration=0.2)
        for _ in range(5):
            self._move(yaw=28,  duration=0.15)
            self._move(yaw=-28, duration=0.15)
        self._move(yaw=55, pitch=0, duration=0.4)
        time.sleep(0.5)
        self._center()
        self._antenna(0, 0)

    # ── Signature behaviors ──────────────────────────────────────────────────

    def _behavior_sniff(self):
        self._move(yaw=-20, pitch=-8,  duration=0.8)
        time.sleep(0.4)
        self._move(yaw=-20, pitch=-16, duration=0.5)
        time.sleep(0.8)
        self._move(pitch=-4, yaw=-10,  duration=0.4)
        time.sleep(0.3)
        self._sign_good_job()

    def _behavior_mirror_stir(self):
        self._sign_stir()

    def _behavior_cut(self):
        self._sign_cut()

    def _behavior_timeout_tilt(self):
        self._antenna(0.3, -0.3, duration=0.5)
        self._move(roll=24, duration=0.8)
        time.sleep(1.6)
        self._center()
        self._antenna(0, 0)

    def _behavior_victory_bow(self):
        self._antenna(1.0, 1.0, duration=0.5)
        self._move(pitch=-30, duration=1.2)
        time.sleep(2.0)
        self._center(duration=0.8)
        self._sign_good_job()

    def _behavior_freeze_and_stare(self, yaw_deg=-30):
        self._center(duration=0.1)
        self._antenna(0, 0, duration=0.1)
        time.sleep(0.6)
        self._move(yaw=yaw_deg, duration=1.2)
        time.sleep(1.2)
        self._sign_warning()


# ── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    
     with ReachyChef() as chef:
        for s in ReachyChef.SIGNS:
            print(f"[SIGN] {s}")
            chef.sign(s)
            time.sleep(0.5)

        for b in ReachyChef.BEHAVIORS:
            print(f"[BEHAVIOR] {b}")
            chef.behavior(b)
            time.sleep(0.8)