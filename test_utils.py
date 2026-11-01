import unittest

from utils import parse_allowed_ids, parse_username


class ParseUsernameTests(unittest.TestCase):
    def test_plain_and_at_forms(self):
        self.assertEqual(parse_username("natgeo"), "natgeo")
        self.assertEqual(parse_username("@NatGeo"), "natgeo")
        self.assertEqual(parse_username("  @some.user_1  "), "some.user_1")

    def test_profile_links(self):
        self.assertEqual(parse_username("https://www.instagram.com/natgeo/"), "natgeo")
        self.assertEqual(parse_username("instagram.com/natgeo?igsh=abc"), "natgeo")
        self.assertEqual(parse_username("http://instagram.com/NatGeo"), "natgeo")

    def test_story_links(self):
        self.assertEqual(
            parse_username("https://www.instagram.com/stories/natgeo/3123456789/"),
            "natgeo",
        )

    def test_link_inside_a_sentence(self):
        self.assertEqual(
            parse_username("please get https://instagram.com/natgeo/ thanks"), "natgeo"
        )

    def test_non_profile_links_are_rejected(self):
        self.assertIsNone(parse_username("https://www.instagram.com/p/ABC123/"))
        self.assertIsNone(parse_username("https://www.instagram.com/reel/XYZ789/"))
        self.assertIsNone(parse_username("https://www.instagram.com/stories/highlights/1789/"))
        self.assertIsNone(parse_username("https://www.instagram.com/explore/"))

    def test_other_sites_are_rejected(self):
        self.assertIsNone(parse_username("https://notinstagram.com/natgeo"))

    def test_invalid_input(self):
        self.assertIsNone(parse_username(""))
        self.assertIsNone(parse_username(None))
        self.assertIsNone(parse_username("hello there"))
        self.assertIsNone(parse_username("a" * 31))


class ParseAllowedIdsTests(unittest.TestCase):
    def test_mixed_separators_and_junk(self):
        self.assertEqual(parse_allowed_ids("1, 2 3,abc"), {1, 2, 3})

    def test_empty(self):
        self.assertEqual(parse_allowed_ids(None), set())
        self.assertEqual(parse_allowed_ids(""), set())


if __name__ == "__main__":
    unittest.main()
