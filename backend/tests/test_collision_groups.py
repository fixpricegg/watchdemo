
import unittest

from library.collision_groups import classify_collision_group


class TestCollisionGroups(unittest.TestCase):

    def group(self, material, flags):
        return {
            "surface_property": material,
            "interact_as": flags,
        }

    def test_concrete_candidate(self):
        self.assertEqual(
            classify_collision_group(self.group("concrete", [])),
            "solid_candidate",
        )

    def test_passbullets(self):
        self.assertEqual(
            classify_collision_group(
                self.group("chainlink", ["passbullets"])
            ),
            "special_passbullets",
        )

    def test_explicit_los_blocker(self):
        self.assertEqual(
            classify_collision_group(
                self.group("metal", ["blocklos", "solid"])
            ),
            "explicit_los_blocker",
        )

    def test_playerclip(self):
        self.assertEqual(
            classify_collision_group(
                self.group("default", ["playerclip"])
            ),
            "special_collision",
        )

    def test_glass_is_uncertain(self):
        self.assertEqual(
            classify_collision_group(self.group("glass", [])),
            "requires_review",
        )

    def test_unknown_flags(self):
        self.assertEqual(
            classify_collision_group(
                self.group("metal", ["unrecognized_flag"])
            ),
            "requires_review",
        )


if __name__ == "__main__":
    unittest.main()
