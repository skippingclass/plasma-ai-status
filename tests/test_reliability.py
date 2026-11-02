import fcntl
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import test_status_provider as fixtures
provider = fixtures.provider


class LongCodexTests(unittest.TestCase):
    def setUp(self):
        self.base = provider.datetime.fromisoformat('2026-10-22T17:00:00+00:00').timestamp()
        self.events = [fixtures.ActivityTests().event('task_started'),
                       fixtures.ActivityTests().event('function_call', 'response_item', call_id='long')]

    def test_long_tool_needs_current_owner_and_completion_always_wins(self):
        now = self.base + 1800
        self.assertEqual(provider.codex_session_status(self.events, now, self.base - 1), 'работает')
        self.assertEqual(provider.codex_session_status(self.events, now), 'отдыхает')
        self.assertEqual(provider.codex_session_status(self.events, now, self.base + 1), 'отдыхает')
        metadata = dict(timestamp='2026-10-22T17:02:00Z', type='session_meta', payload={})
        self.assertEqual(provider.codex_session_status(self.events + [metadata], now, self.base + 1), 'отдыхает')
        for final in [fixtures.ActivityTests().event('task_complete'), fixtures.ActivityTests().event('turn_aborted'),
                      fixtures.ActivityTests().event('message', 'response_item', role='assistant', phase='final_answer')]:
            self.assertEqual(provider.codex_session_status(self.events + [final], now, self.base - 1), 'отдыхает')
        self.assertEqual(provider.codex_session_status(self.events[:1], now, self.base - 1), 'думает')

    def test_old_owned_rollout_is_read_even_when_recent_candidate_limit_is_full(self):
        with tempfile.TemporaryDirectory() as root:
            old = Path(root) / 'old.jsonl'
            old.touch()
            with patch.object(provider, 'codex_running', return_value=True), \
                    patch.object(provider, 'codex_owned_sessions', return_value={str(old): self.base - 1}), \
                    patch.object(provider.glob, 'glob', return_value=['new' + str(i) for i in range(20)]), \
                    patch.object(provider.os.path, 'getmtime', return_value=self.base + 1799), \
                    patch.object(provider, 'tail_events', side_effect=lambda p: self.events if p == str(old) else []), \
                    patch.object(provider.time, 'time', return_value=self.base + 1800):
                self.assertEqual(provider.check_codex_status(), 'работает')

    def test_only_writable_logs_in_codex_home_with_readable_live_owner_are_kept(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'CODEX_HOME': root + '/codex'}):
            proc = Path(root) / 'proc'
            proc.mkdir()
            (proc / 'stat').write_text('btime 1700000000\n')
            pid = proc / '10'
            (pid / 'fd').mkdir(parents=True)
            (pid / 'fdinfo').mkdir()
            (pid / 'stat').write_text('10 (codex with spaces) ' + ' '.join(
                ['S', '1'] + ['0'] * 17 + [str(100 * os.sysconf('SC_CLK_TCK'))]))
            sessions = Path(root) / 'codex/sessions'
            sessions.mkdir(parents=True)
            for index, mode in enumerate(('02', '00')):
                target = sessions / f'{index}.jsonl'
                target.touch()
                (pid / 'fd' / str(index)).symlink_to(target)
                (pid / 'fdinfo' / str(index)).write_text('flags:\t' + mode + '\n')
            with patch.object(provider, 'codex_pids', return_value=[10]):
                self.assertEqual(provider.codex_owned_sessions(str(proc)), {str(sessions / '0.jsonl'): 1700000100})
                (pid / 'stat').unlink()
                self.assertEqual(provider.codex_owned_sessions(str(proc)), {})


class ForcedQuotaTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {
            'XDG_STATE_HOME': self.directory.name + '/state',
            'XDG_CACHE_HOME': self.directory.name + '/cache'})
        self.environment.start()
        self.path, self.lock = provider.cache_paths('codex')
        self.now = time.time()
        provider.write_cache(self.path, dict(attempted_at=self.now-10, timestamp=self.now-100,
            bar1_percent=45, bar1_updated_at=self.now-100, bar2_percent=20, bar2_updated_at=self.now-500))

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def test_force_bypasses_ttl_but_not_five_second_cooldown(self):
        with patch.object(provider, 'fetch_codex_quota', return_value=dict(bar1_percent=40)) as fetch:
            provider.refresh_quota('codex')
            fetch.assert_not_called()
            provider.refresh_quota('codex', force=True)
            provider.refresh_quota('codex', force=True)
            self.assertEqual(fetch.call_count, 1)
        saved = provider.read_cache(self.path)
        self.assertEqual(saved['bar1_percent'], 40)
        self.assertEqual(saved['bar2_percent'], 20)
        self.assertEqual(saved['bar2_updated_at'], self.now-500)

    def test_concurrent_refresh_is_coalesced_and_reported_as_refreshing(self):
        cached = provider.read_cache(self.path)
        cached['refreshing_until'] = time.time() + 60
        provider.write_cache(self.path, cached)
        with open(self.lock, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(provider, 'fetch_codex_quota') as fetch:
                provider.refresh_quota('codex', force=True)
                fetch.assert_not_called()
            self.assertTrue(provider.get_usage('codex')['quota_refreshing'])
        cached['refreshing_until'] = time.time() - 1
        provider.write_cache(self.path, cached)
        self.assertFalse(provider.get_usage('codex')['quota_refreshing'])

    def test_progress_is_visible_during_fetch_and_cleared_after_success(self):
        def fetch():
            self.assertTrue(provider.get_usage('codex')['quota_refreshing'])
            return dict(bar1_percent=40)
        with patch.object(provider, 'fetch_codex_quota', side_effect=fetch):
            provider.refresh_quota('codex', force=True)
        self.assertFalse(provider.get_usage('codex')['quota_refreshing'])

    def test_failed_force_preserves_success_time_and_values(self):
        with patch.object(provider, 'fetch_codex_quota', side_effect=RuntimeError('offline')):
            provider.refresh_quota('codex', force=True)
        saved = provider.read_cache(self.path)
        self.assertEqual(saved['bar1_percent'], 45)
        self.assertEqual(saved['bar1_updated_at'], self.now-100)
        self.assertEqual(saved['timestamp'], self.now-100)
        self.assertEqual(saved['quota_error'], 'offline')
