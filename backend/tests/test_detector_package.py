
import unittest

import detectors

from detectors.entry_candidates import (
    detect_potentially_bad_entries,
)
from detectors.missed_trade import (
    get_possible_missed_trades,
)


class TestDetectorPackage(unittest.TestCase):

    def test_entry_export(self):
        self.assertIs(
            detectors.detect_potentially_bad_entries,
            detect_potentially_bad_entries,
        )

    def test_missed_trade_import(self):
        self.assertTrue(
            callable(get_possible_missed_trades)
        )


if __name__ == "__main__":
    unittest.main()
