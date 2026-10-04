"""핵심 분기 로직 테스트 (constitution VI). 네트워크 없이 돈다: py -m unittest -v"""
import os
import socket
import tempfile
import unittest
from pathlib import Path

import alarm
from mercari import Item

NOW = 1_790_000_000


def item(id, created=NOW, name="ポケカ", price=1000):
    return Item(id, name, price, created)


class DecideTest(unittest.TestCase):
    def test_first_run_is_silent_and_records_everything(self):
        state, fresh, saturated = alarm.decide(None, [item("a"), item("b")], NOW)
        self.assertEqual(fresh, [])
        self.assertFalse(saturated)
        self.assertEqual(state, {"since": NOW, "seen": ["a", "b"]})

    def test_unseen_item_created_after_since_is_fresh(self):
        st = {"since": NOW, "seen": ["a"]}
        _, fresh, _ = alarm.decide(st, [item("b", NOW + 30), item("a")], NOW + 60)
        self.assertEqual([i.id for i in fresh], ["b"])

    def test_clock_slack_allows_slightly_older_created(self):
        st = {"since": NOW, "seen": []}
        _, fresh, _ = alarm.decide(st, [item("b", NOW - alarm.CLOCK_SLACK)], NOW + 60)
        self.assertEqual(len(fresh), 1)

    def test_bumped_old_item_is_recorded_not_notified(self):
        st = {"since": NOW, "seen": ["a"]}
        state, fresh, _ = alarm.decide(st, [item("old", NOW - 86400), item("a")], NOW + 60)
        self.assertEqual(fresh, [])
        self.assertIn("old", state["seen"])

    def test_seen_item_is_ignored(self):
        st = {"since": NOW, "seen": ["a"]}
        _, fresh, saturated = alarm.decide(st, [item("a", NOW + 10)], NOW + 60)
        self.assertEqual(fresh, [])
        self.assertFalse(saturated)

    def test_fresh_keeps_list_order_and_is_not_capped(self):
        st = {"since": NOW, "seen": []}
        items = [item(str(n), NOW + 100 - n) for n in range(8)]
        _, fresh, _ = alarm.decide(st, items, NOW + 200)
        self.assertEqual([i.id for i in fresh], [str(n) for n in range(8)])
        # 개별 5건 + 묶음 3건은 run 쪽에서 fresh[:BURST] / fresh[BURST:]로 나눈다
        self.assertEqual(len(fresh[alarm.BURST:]), 3)

    def test_full_window_of_unseen_means_saturated(self):
        st = {"since": NOW, "seen": ["x"]}
        full = [item(str(n)) for n in range(alarm.mercari.PAGE_SIZE - 5)]
        _, _, saturated = alarm.decide(st, full, NOW + 60)
        self.assertTrue(saturated)
        _, _, saturated = alarm.decide(st, full + [item("x")], NOW + 60)
        self.assertFalse(saturated)

    def test_few_unseen_results_are_not_saturated(self):
        st = {"since": NOW, "seen": ["x"]}
        _, _, saturated = alarm.decide(st, [item("a"), item("b")], NOW + 60)
        self.assertFalse(saturated)

    def test_item_still_in_window_is_not_forgotten(self):
        # 오래 기억한 A가 아직 목록에 뜨면 뒤로 옮겨져, 이후 ID가 쌓여도 잘리지 않는다
        st = {"since": NOW, "seen": ["A"] + [str(n) for n in range(alarm.SEEN_LIMIT - 1)]}
        state, _, _ = alarm.decide(st, [item("A", NOW + 10), item("old", NOW - 86400)], NOW + 60)
        self.assertEqual(state["seen"][-2:], ["A", "old"])
        self.assertEqual(len(state["seen"]), alarm.SEEN_LIMIT)

    def test_seen_is_trimmed_to_limit(self):
        st = {"since": NOW, "seen": [str(n) for n in range(alarm.SEEN_LIMIT)]}
        state, _, _ = alarm.decide(st, [item("old", NOW - 86400)], NOW + 60)
        self.assertEqual(len(state["seen"]), alarm.SEEN_LIMIT)
        self.assertEqual(state["seen"][-1], "old")


class ItemMessageTest(unittest.TestCase):
    def test_translated_with_original(self):
        msg = alarm.item_message(item("a", name="ポケカ BOX", price=12800), "포켓몬 카드 BOX")
        self.assertEqual(msg, "포켓몬 카드 BOX\n¥12,800\n(ポケカ BOX)")

    def test_translation_failed_shows_original_only(self):
        msg = alarm.item_message(item("a", name="ポケカ BOX", price=12800), None)
        self.assertEqual(msg, "ポケカ BOX\n¥12,800")

    def test_translation_same_as_original_is_not_repeated(self):
        msg = alarm.item_message(item("a", name="PSA10", price=500), "PSA10")
        self.assertEqual(msg, "PSA10\n¥500")


class KeywordTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        self._orig = alarm.KEYWORDS_FILE, alarm.STATE_FILE
        alarm.KEYWORDS_FILE, alarm.STATE_FILE = d / "keywords.txt", d / "state.json"
        self.addCleanup(lambda: setattr(alarm, "KEYWORDS_FILE", self._orig[0]))
        self.addCleanup(lambda: setattr(alarm, "STATE_FILE", self._orig[1]))

    def test_validate_strips_whitespace(self):
        self.assertEqual(alarm.validate_keyword("  ポケカ  ", []), "ポケカ")

    def test_validate_rejects_empty_and_too_long(self):
        for bad in ["", "   ", "あ" * (alarm.MAX_LEN + 1)]:
            with self.assertRaisesRegex(ValueError, "1~50자"):
                alarm.validate_keyword(bad, [])
        self.assertEqual(alarm.validate_keyword("あ" * alarm.MAX_LEN, []), "あ" * alarm.MAX_LEN)

    def test_validate_rejects_exact_duplicate_only(self):
        with self.assertRaisesRegex(ValueError, "이미 등록"):
            alarm.validate_keyword("ポケカ", ["ポケカ"])
        self.assertEqual(alarm.validate_keyword("ﾎﾟｹｶ", ["ポケカ"]), "ﾎﾟｹｶ")

    def test_validate_rejects_line_breaks(self):
        for bad in ["ポケカ\nスイッチ", "ポケカ\u2028スイッチ", "ポケカ\x0bスイッチ"]:
            with self.assertRaisesRegex(ValueError, "줄바꿈"):
                alarm.validate_keyword(bad, [])

    def test_validate_rejects_over_limit(self):
        existing = [str(n) for n in range(alarm.MAX_KEYWORDS)]
        with self.assertRaisesRegex(ValueError, "최대 20개"):
            alarm.validate_keyword("new", existing)

    def test_add_and_remove_update_file_and_state(self):
        self.assertEqual(alarm.add_keyword(" ポケカ "), ["ポケカ"])
        self.assertEqual(alarm.KEYWORDS_FILE.read_text(encoding="utf-8"), "ポケカ\n")
        alarm.save_state({"ポケカ": {"since": NOW, "seen": []}})
        self.assertEqual(alarm.remove_keyword("ポケカ"), [])
        self.assertEqual(alarm.load_state(), {})
        with self.assertRaises(KeyError):
            alarm.remove_keyword("ポケカ")

    def test_load_skips_invalid_lines_and_bom(self):
        alarm.KEYWORDS_FILE.write_text("﻿ポケカ\n\n  ポケカ \n" + "あ" * 51 + "\nスイッチ\n", encoding="utf-8")
        self.assertEqual(alarm.load_keywords(), ["ポケカ", "スイッチ"])


class LoadEnvTest(unittest.TestCase):
    def test_inline_comment_and_comment_lines_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text("# 주석\nMA_T1=abc  # 내 토픽\nMA_T2=x#y\nMA_T3=v\t# tab\n", encoding="utf-8")
            alarm.load_env(p)
        self.assertEqual((os.environ.pop("MA_T1"), os.environ.pop("MA_T2"), os.environ.pop("MA_T3")), ("abc", "x#y", "v"))


class FailureWatchTest(unittest.TestCase):
    def test_slow_query_does_not_reset_failure(self):
        w = alarm.FailureWatch(NOW, 0)
        self.assertEqual(w.tick(NOW + 600, 600), 0)
        self.assertEqual(w.last_success, NOW)
        self.assertTrue(w.should_alert(NOW + 600))

    def test_sleep_resets_failure_until_ten_minutes_after_wake(self):
        w = alarm.FailureWatch(NOW, 0)
        self.assertEqual(w.tick(NOW + 3600, 60), 3540)
        self.assertEqual(w.last_success, NOW + 3600)
        self.assertFalse(w.should_alert(NOW + 3600))
        self.assertTrue(w.should_alert(NOW + 4200))
        self.assertEqual(w.tick(NOW + 4200, 660), 0)

    def test_short_sleep_does_not_reset_failure(self):
        w = alarm.FailureWatch(NOW, 0)
        self.assertEqual(w.tick(NOW + 119, 60), 59)
        self.assertEqual(w.last_success, NOW)

    def test_alerts_once_after_threshold_and_resets_on_success(self):
        w = alarm.FailureWatch(NOW)
        self.assertFalse(w.should_alert(NOW))
        self.assertFalse(w.should_alert(NOW + alarm.FAIL_ALERT_SEC - 1))
        self.assertTrue(w.should_alert(NOW + alarm.FAIL_ALERT_SEC))
        # 전송 실패(mark_alerted 안 함) → 다음 주기에 다시 시도
        self.assertTrue(w.should_alert(NOW + alarm.FAIL_ALERT_SEC + 60))
        w.mark_alerted()
        self.assertFalse(w.should_alert(NOW + alarm.FAIL_ALERT_SEC + 120))
        w.ok(NOW + 1000)
        self.assertFalse(w.should_alert(NOW + 1000 + alarm.FAIL_ALERT_SEC - 1))
        self.assertTrue(w.should_alert(NOW + 1000 + alarm.FAIL_ALERT_SEC))


class ClientCheckTest(unittest.TestCase):
    def test_allows_loopback_and_tailscale(self):
        for ip in ["127.0.0.1", "127.255.255.254", "100.64.0.1", "100.127.255.254", "100.101.102.103"]:
            self.assertTrue(alarm.client_allowed(ip), ip)

    def test_rejects_lan_outside_tailscale_and_invalid(self):
        for ip in ["192.168.0.10", "10.0.0.5", "100.63.255.255", "100.128.0.1", "8.8.8.8", "invalid", ""]:
            self.assertFalse(alarm.client_allowed(ip), ip)


class HostCheckTest(unittest.TestCase):
    def test_allows_ip_localhost_lan_name_and_tailscale(self):
        pc = socket.gethostname()
        for host in ["100.101.102.103:8787", "192.168.0.10", "localhost:8787", f"{pc}:8787", f"{pc.upper()}.local",
                     "my-pc.tail1234.ts.net:8787", "[::1]:8787"]:
            self.assertTrue(alarm.host_allowed(host), host)

    def test_rejects_other_domains(self):
        for host in ["evil.example.com", "evil.example.com:8787", "", "evil.example.com@localhost", "[abc",
                     "other-pc", "2130706433"]:
            self.assertFalse(alarm.host_allowed(host), host)


if __name__ == "__main__":
    unittest.main()
