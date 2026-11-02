"""Linux process and quota fixtures for desktop/CLI coexistence."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

from test_status_provider import provider


def process(root, pid, args, parent=1):
    directory = Path(root) / str(pid)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'cmdline').write_bytes(('\0'.join(args) + '\0').encode())
    (directory / 'stat').write_text(f'{pid} (process with spaces) S {parent} 0 0')
    return directory


class DesktopSourceTests(unittest.TestCase):
    def test_gui_detection_includes_appimage_and_marked_server_only(self):
        with tempfile.TemporaryDirectory() as root:
            commands = {
                1: ['/tmp/.mount_Antigr123/antigravity'],
                2: ['/opt/antigravity/Antigravity.AppImage'],
                3: ['/tmp/.mount_Antigr123/resources/bin/language_server',
                    '--app_data_dir', 'antigravity', '--csrf_token', 'test-token'],
                4: ['/usr/bin/language_server', '--app_data_dir=antigravity-ide'],
                5: ['antigravity', '--type=renderer'],
                6: ['antigravity', '--type', 'zygote'],
                7: ['/some/other/language_server', '--csrf_token', 'not-ours'],
                8: ['agy', '-p', '/usage'],
                9: ['antigravity', '--version'],
                10: ['python', 'antigravity'],
            }
            for pid, args in commands.items():
                process(root, pid, args)
            self.assertEqual(set(provider.antigravity_gui_pids(root)), {1, 2, 3, 4})
            with patch.object(provider.os, 'getuid', return_value=os.getuid() + 1):
                self.assertEqual(provider.antigravity_gui_pids(root), [])

    def test_gui_open_database_is_used_for_activity(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as root:
            proc = process(root, 10, ['language_server', '--app_data_dir', 'antigravity'])
            db = Path(root) / 'antigravity/conversations/session.db'
            db.parent.mkdir(parents=True)
            connection = sqlite3.connect(db)
            connection.execute('CREATE TABLE steps (idx, step_type, status, metadata, step_payload)')
            connection.execute("INSERT INTO steps VALUES (1, 15, 2, X'', X'')")
            connection.commit()
            (proc / 'fd').mkdir()
            (proc / 'fd/7').symlink_to(db)
            databases, log = provider.inspect_pid_fds(10, root)
            self.assertEqual(databases, [str(db)])
            self.assertEqual(provider.check_db_status(databases[0], time.time()), 'думает')
            connection.execute('UPDATE steps SET step_type=132')
            connection.commit()
            self.assertEqual(provider.check_db_status(databases[0], time.time()), 'работает')
            connection.execute('UPDATE steps SET step_type=15,status=3')
            connection.commit()
            self.assertEqual(provider.check_db_status(databases[0], time.time()), 'отдыхает')
            connection.close()

    def test_presence_lock_resolves_its_own_gui_or_cli_profile(self):
        with tempfile.TemporaryDirectory() as root:
            proc = process(root, 1, ['agy'])
            (proc / 'fd').mkdir()
            expected = set()
            for index, name in enumerate(('antigravity', 'antigravity-cli')):
                profile = Path(root) / name
                (profile / 'presence').mkdir(parents=True)
                (profile / 'conversations').mkdir()
                lock = profile / 'presence/session.lock'
                lock.touch()
                db = profile / 'conversations/session.db'
                db.touch()
                (proc / 'fd' / str(index)).symlink_to(lock)
                expected.add(str(db))
            self.assertEqual(set(provider.inspect_pid_fds(1, root)[0]), expected)

    def test_gui_cancel_log_must_belong_to_the_same_server(self):
        with tempfile.TemporaryDirectory() as root:
            process(root, 10, ['language_server', '--app_data_dir', 'antigravity'])
            config = Path(root) / 'config'
            log = config / 'Antigravity/logs/language_server.log'
            log.parent.mkdir(parents=True)
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': str(config)}):
                log.write_text('Starting language server process with pid 100\n')
                self.assertIsNone(provider.inspect_pid_fds(10, root)[1])
                log.write_text('Starting language server process with pid 10\n')
                self.assertEqual(provider.inspect_pid_fds(10, root)[1], str(log))

    def test_only_process_owned_listening_ports_are_probed(self):
        with tempfile.TemporaryDirectory() as root:
            proc = process(root, 1, ['language_server'])
            (proc / 'fd').mkdir()
            (proc / 'net').mkdir()
            (proc / 'fd/4').symlink_to('socket:[123]')
            # The kernel's tcp table is namespace-wide: inode matching is essential.
            (proc / 'net/tcp').write_text(
                'header\n0: 0100007F:8080 0:0 0A 0 0 0 0 0 123\n'
                '1: 0100007F:9090 0:0 0A 0 0 0 0 0 999\n'
                '2: 0100007F:7070 0:0 01 0 0 0 0 0 123\n')
            self.assertEqual(provider.listening_ports(1, root), [32896])

    def test_gui_quota_shape_preserves_zero_unknown_and_separate_argon_group(self):
        data = {'response': {'groups': [
            {'displayName': 'Gemini 4 Argon', 'buckets': [
                {'bucketId': 'argon-weekly', 'window': 'weekly', 'remainingFraction': 1}]},
            {'displayName': 'Gemini Models', 'buckets': [
                {'bucketId': 'gemini-5h', 'remainingFraction': 0,
                 'resetTime': '2026-11-03T12:00:00Z'},
                {'bucketId': 'gemini-weekly', 'remaining': {'remainingFraction': .646}}]}]}}
        quota = provider.parse_agy_quota(data)
        self.assertEqual(quota['bar1_percent'], 0)
        self.assertEqual(quota['bar2_exact'], 64.6)
        self.assertGreater(quota['bar1_resets_at'], 0)
        data['response']['groups'][1]['buckets'] = [
            {'bucketId': 'gemini-5h'},
            {'bucketId': 'gemini-weekly', 'enabled': False, 'remainingFraction': 1}]
        self.assertIsNone(provider.parse_agy_quota(data))

    def test_gui_quota_preferred_and_cli_used_only_when_unavailable(self):
        with patch.object(provider, 'fetch_antigravity_gui_quota', return_value={'bar1_percent': 0}), \
                patch.object(provider, 'fetch_agy_quota') as cli:
            self.assertEqual(provider.fetch_antigravity_quota(), {'bar1_percent': 0})
            cli.assert_not_called()
        with patch.object(provider, 'fetch_antigravity_gui_quota', return_value=None), \
                patch.object(provider, 'fetch_agy_quota', return_value={'bar1_percent': 41}):
            self.assertEqual(provider.fetch_antigravity_quota()['bar1_percent'], 41)

    def test_gui_http_probe_handles_failed_port_without_leaking_token(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            'response': {'groups': [{'displayName': 'Gemini Models', 'buckets': [
                {'bucketId': 'gemini-5h', 'remainingFraction': .7}]}]}}).encode()
        opener = MagicMock()
        opener.open.side_effect = [OSError('not TLS'), response]
        with patch.object(provider, 'antigravity_gui_pids', return_value=[1]), \
                patch.object(provider, 'process_args', return_value=[
                    'language_server', '--app_data_dir', 'antigravity', '--csrf_token=test-token']), \
                patch.object(provider, 'listening_ports', return_value=[12345]), \
                patch.object(provider.urllib.request, 'build_opener', return_value=opener):
            self.assertEqual(provider.fetch_antigravity_gui_quota()['bar1_percent'], 70)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url,
            'http://127.0.0.1:12345/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary')
        self.assertEqual(request.get_header('X-codeium-csrf-token'), 'test-token')
        self.assertEqual(request.data, b'{}')

    def test_idle_gui_and_busy_cli_are_combined(self):
        with patch.object(provider, 'check_single_pid_status', side_effect=['отдыхает', 'работает']):
            self.assertEqual(provider.check_agy_status([1, 2]), 'работает')
        with patch.object(provider, 'inspect_pid_fds', return_value=([], None)), \
                patch.object(provider, 'process_args', return_value=['antigravity']):
            self.assertEqual(provider.check_single_pid_status(1, time.time()), 'отдыхает')

    def test_codex_app_server_excludes_only_widgets_own_probe(self):
        with tempfile.TemporaryDirectory() as root:
            process(root, 10, ['python3', '/widget/status_provider.py', '--provider', 'codex', '--refresh-only'])
            process(root, 11, ['codex', 'app-server'], parent=10)
            self.assertFalse(provider.codex_running(root))
            process(root, 20, ['/opt/codex/Codex'])
            process(root, 21, ['codex', 'app-server'], parent=20)
            self.assertTrue(provider.codex_running(root))
            (Path(root) / '20/cmdline').write_bytes(b'unrelated\0')
            self.assertTrue(provider.codex_running(root))
            with patch.object(provider.os, 'getuid', return_value=os.getuid() + 1):
                self.assertFalse(provider.codex_running(root))

    def test_codex_helpers_and_login_do_not_mark_app_running(self):
        with tempfile.TemporaryDirectory() as root:
            process(root, 1, ['Codex', '--type=renderer'])
            process(root, 2, ['codex', 'login'])
            process(root, 3, ['codex', '--version'])
            self.assertFalse(provider.codex_running(root))

    def test_codex_idle_desktop_server_is_resting_without_recent_rollouts(self):
        with patch.object(provider, 'codex_running', return_value=True), \
                patch.object(provider.glob, 'glob', return_value=[]):
            self.assertEqual(provider.check_codex_status(), 'отдыхает')
