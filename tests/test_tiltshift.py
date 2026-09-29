"""python -m unittest discover -s tests -t .   (no game needed: uses small stand-in shader files)"""
import tempfile
import unittest
from pathlib import Path

from tiltshift import game, settings, shaders

COMPOSE_SRC = "#version 150\nvoid main() {\n\tvec3 col = vec3(1.0);\n\tcolor.rgb = col;\n}\n"
SSR_SRC = "#version 150\nvoid main() {\n\tcolor = vec4(1.0);\n}\n"


def fake_game(root: Path) -> Path:
    (root / game.GAME_EXE).write_text("")
    for rel, text in ((game.COMPOSE, COMPOSE_SRC), (game.SSR, SSR_SRC)):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    return root


class Defaults(unittest.TestCase):
    def test_every_setting_has_a_default_from_the_shaders(self):
        values = settings.defaults()
        self.assertEqual(set(values), {s.key for s in settings.SETTINGS})
        self.assertEqual(values["TS_MAX_BLUR"], 9.75)          # the look approved in game on 2026-09-30
        self.assertEqual(values["TS_FOCUS_NEAR_BIAS"], 1.6)
        self.assertEqual(values["TS_TAPS"], 48)

    def test_defaults_are_inside_their_slider_ranges(self):
        for key, value in settings.defaults().items():
            self.assertEqual(settings.clamp(settings.BY_KEY[key], value), value, key)


class Constants(unittest.TestCase):
    def test_numbers_are_valid_glsl(self):
        self.assertEqual(shaders.glsl_number(400, "float"), "400.0")
        self.assertEqual(shaders.glsl_number(0.125, "float"), "0.125")
        self.assertEqual(shaders.glsl_number(47.6, "int"), "48")

    def test_set_constants_changes_only_the_given_values(self):
        text = "const float TS_A = 1.0;  // a\nconst int   TS_B = 2;\n"
        out = shaders.set_constants(text, {"TS_A": 3.5})
        self.assertEqual(out, "const float TS_A = 3.5;  // a\nconst int   TS_B = 2;\n")
        self.assertEqual(shaders.read_constants(out), {"TS_A": 3.5, "TS_B": 2.0})


class Patching(unittest.TestCase):
    def test_patched_shaders_carry_the_settings(self):
        values = dict(settings.defaults(), TS_MAX_BLUR=12.0)
        ssr = shaders.patch_ssr(SSR_SRC, values)
        self.assertIn("void ssrMain() {", ssr)
        self.assertIn("const float TS_MAX_BLUR = 12.0;", ssr)
        self.assertEqual(ssr.count("void main() {"), 1)
        compose = shaders.patch_compose(COMPOSE_SRC, values)
        self.assertIn("col = tsGrade(col);\n\tcolor.rgb = col;", compose)
        self.assertIn(shaders.MARKER, ssr + compose)

    def test_changed_game_shader_is_refused(self):
        with self.assertRaises(shaders.PatchError):
            shaders.patch_ssr("void main2() {}", settings.defaults())


class Install(unittest.TestCase):
    def test_apply_restore_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fake_game(Path(tmp))
            game.apply(root, settings.defaults())
            self.assertTrue(game.is_patched(root, game.COMPOSE) and game.is_patched(root, game.SSR))
            game.apply(root, dict(settings.defaults(), TS_MAX_BLUR=5.0))      # re-apply patches the ORIGINAL again
            self.assertEqual((root / game.SSR).read_text().count("void ssrMain() {"), 1)
            game.restore_all(root)
            self.assertEqual((root / game.SSR).read_text(), SSR_SRC)
            self.assertEqual((root / game.COMPOSE).read_text(), COMPOSE_SRC)
            self.assertFalse(list(root.rglob("*" + game.BACKUP_SUFFIX)))

    def test_switching_a_part_off_restores_that_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fake_game(Path(tmp))
            game.apply(root, settings.defaults())
            game.apply(root, dict(settings.defaults(), enable_colour=0.0))
            self.assertEqual((root / game.COMPOSE).read_text(), COMPOSE_SRC)
            self.assertTrue(game.is_patched(root, game.SSR))

    def test_game_update_replaces_the_stale_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fake_game(Path(tmp))
            game.apply(root, settings.defaults())
            updated = SSR_SRC.replace("vec4(1.0)", "vec4(0.5)")          # Steam update / verify rewrites the file
            (root / game.SSR).write_text(updated)
            game.apply(root, settings.defaults())
            self.assertIn("vec4(0.5)", (root / game.SSR).read_text())
            game.restore_all(root)
            self.assertEqual((root / game.SSR).read_text(), updated)


if __name__ == "__main__":
    unittest.main()
