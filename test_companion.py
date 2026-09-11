import unittest

import companion


class ReactionPriorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = companion.load_config()
        self.context = dict(
            now=100.0,
            process="chrome.exe",
            idle=0.0,
            manual=None,
            after=None,
            director=None,
            director_reason="",
            director_priority=companion.REACTION_PRIORITY["director"],
            volume_recent=False,
            volume_level=0.5,
            volume_muted=False,
            last_key=0.0,
            last_scroll=99.5,
            scroll_burst=2,
            config=self.config,
            games={"wow.exe"},
            browsers={"chrome.exe"},
            media={"spotify.exe"},
            app_states={"discord.exe": "notification"},
        )

    def choose(self, **changes):
        context = self.context | changes
        return companion.choose_reaction(**context)

    def test_browser_scroll_beats_idle(self):
        self.assertEqual(self.choose()[0], "browsing")

    def test_game_beats_typing(self):
        self.assertEqual(self.choose(process="wow.exe", last_key=99.9, last_scroll=0)[0], "gaming")

    def test_volume_beats_game(self):
        self.assertEqual(self.choose(process="wow.exe", volume_recent=True)[0], "volume")

    def test_manual_beats_everything(self):
        self.assertEqual(self.choose(process="wow.exe", volume_recent=True, manual="rage")[0], "rage")

    def test_director_beats_game_but_not_volume(self):
        self.assertEqual(self.choose(process="wow.exe", director="showoff")[0], "showoff")
        self.assertEqual(self.choose(process="wow.exe", director="showoff", volume_recent=True)[0], "volume")


class TouchTests(unittest.TestCase):
    def setUp(self) -> None:
        companion.APP_CONFIG = companion.load_config()
        companion.RUNTIME = companion.Runtime()

    def test_tap_clears_and_queues_nervous_after_reaction(self):
        companion.RUNTIME.unread_notifications = 3
        self.assertEqual(companion.RUNTIME.touch_reaction("tap"), 3)
        snapshot = companion.RUNTIME.snapshot()
        self.assertEqual(snapshot["state"], "rage")
        self.assertEqual(snapshot["unread_notifications"], 0)
        self.assertEqual(companion.RUNTIME.after_state, "nervous")

    def test_double_and_hold_do_not_clear(self):
        companion.RUNTIME.unread_notifications = 2
        companion.RUNTIME.touch_reaction("double")
        self.assertEqual(companion.RUNTIME.snapshot()["state"], "helper")
        companion.RUNTIME.touch_reaction("hold")
        snapshot = companion.RUNTIME.snapshot()
        self.assertEqual(snapshot["state"], "sleep")
        self.assertEqual(snapshot["unread_notifications"], 2)

    def test_swipes_cycle_faces_without_clearing_notifications(self):
        companion.RUNTIME.unread_notifications = 2
        companion.RUNTIME.touch_reaction("swipe_left")
        self.assertEqual(companion.RUNTIME.snapshot()["state"], "cat")
        companion.RUNTIME.touch_reaction("swipe_right")
        snapshot = companion.RUNTIME.snapshot()
        self.assertEqual(snapshot["state"], "idle")
        self.assertEqual(snapshot["unread_notifications"], 2)


class EmotionDirectorTests(unittest.TestCase):
    def setUp(self) -> None:
        companion.APP_CONFIG = companion.load_config()
        companion.RUNTIME = companion.Runtime()

    def test_cooldown_prevents_immediate_repeat(self):
        self.assertTrue(companion.RUNTIME.direct_reaction("cat", 1, "test", cooldown=30))
        self.assertFalse(companion.RUNTIME.direct_reaction("cat", 1, "test", cooldown=30))
        self.assertIn("cooldown", companion.RUNTIME.diagnostic_log()[0]["reason"])

    def test_launch_glyph_and_orc_states_are_supported(self):
        for state in ("launch_chrome", "launch_spotify", "launch_discord",
                      "orc", "orc_happy", "orc_focus", "orc_rage"):
            self.assertIn(state, companion.VALID_STATES)


class HardwareProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        companion.APP_CONFIG = companion.load_config()
        companion.RUNTIME = companion.Runtime()

    def test_wire_frame_is_fixed_and_contains_state(self):
        companion.RUNTIME.state = "browsing_fast"
        companion.RUNTIME.sequence = 42
        companion.RUNTIME.volume_level = 0.75
        companion.RUNTIME.volume_muted = False
        companion.RUNTIME.music_playing = True
        frame = companion.RUNTIME.wire_frame()
        parts = frame.strip().split("|")
        expected_brightness = str(companion.current_display_profile(companion.APP_CONFIG)["brightness"])
        self.assertEqual(parts[:7], ["LILBOT", "1", "42", "browsing_fast", "75", "0", "1"])
        self.assertEqual(parts[7:10], [expected_brightness, "1", "0"])
        self.assertEqual(parts[11], "--")

    def test_wire_frame_contains_privacy_safe_gaze_direction(self):
        companion.RUNTIME.gaze_direction = -1
        companion.RUNTIME.gaze_until = 10**12
        self.assertEqual(companion.RUNTIME.wire_frame().strip().split("|")[13], "-1")


if __name__ == "__main__":
    unittest.main()
