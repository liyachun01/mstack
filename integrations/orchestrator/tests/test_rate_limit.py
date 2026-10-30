"""MST-41: one Linear read per board per tick, the hub owns Linear I/O, and 429s back off for every process."""
import contextlib
import fcntl
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli
import linear
import linear_board
import test_linear_board as flow     # its classes stay out of this module, so its tests run once


class Resp(io.BytesIO):
    def __init__(self, body, headers=None):
        super().__init__(body)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class Backoff(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        p = patch.object(linear, 'BACKOFF_FILE', Path(temp.name)/'backoff.json'); p.start(); self.addCleanup(p.stop)
        self.clock = [1_000_000.0]
        p = patch.object(linear.time, 'time', lambda: self.clock[0]); p.start(); self.addCleanup(p.stop)
        self.sent = []

    def opener(self, *answers):
        answers = list(answers)

        def open_(req, timeout):
            self.sent.append(req)
            answer = answers.pop(0) if len(answers) > 1 else answers[0]
            if isinstance(answer, Exception):
                raise answer
            return answer
        return open_

    def limited(self, headers=None, code=429, body=b''):
        return urllib.error.HTTPError('u', code, 'Too Many Requests', headers or {}, io.BytesIO(body))

    def test_429_waits_for_retry_after_in_every_process_and_logs_once(self):
        err = io.StringIO()
        post = linear.http('k', opener=self.opener(self.limited({'Retry-After': '120'}), Resp(b'{"data": {"ok": 1}}')))
        with contextlib.redirect_stderr(err):
            with self.assertRaises(linear.RateLimited) as hit:
                post('q', {})
            self.assertEqual(hit.exception.until, self.clock[0] + 120)
            other = linear.http('k', opener=self.opener(Resp(b'{"data": {"ok": 2}}')))   # another process, same key
            for call in (post, other, post):
                with self.assertRaises(linear.RateLimited):
                    call('q', {})
        self.assertEqual(len(self.sent), 1)                       # nothing sent while the backoff is on
        self.assertEqual(err.getvalue().count('rate limit'), 1)   # logged once, when it started
        self.assertNotIn('k', json.loads(linear.BACKOFF_FILE.read_text()))   # stored by key hash, never the key
        self.assertEqual(linear.http('other-key', opener=self.opener(Resp(b'{"data": {"ok": 3}}')))('q', {}), {'ok': 3})
        self.clock[0] += 121
        self.assertEqual(post('q', {}), {'ok': 1})

    def test_ratelimited_graphql_error_uses_linear_reset_headers(self):
        reset = str(int((self.clock[0] + 300) * 1000))
        body = json.dumps({'errors': [{'message': 'Rate limit exceeded', 'extensions': {'code': 'RATELIMITED'}}]}).encode()
        post = linear.http('k', opener=self.opener(self.limited(
            {'X-RateLimit-Requests-Remaining': '0', 'X-RateLimit-Requests-Reset': reset}, code=400, body=body)))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(linear.RateLimited) as hit:
            post('q', {})
        self.assertAlmostEqual(hit.exception.until, self.clock[0] + 300, delta=1)

    def test_used_up_budget_on_a_good_answer_waits_for_the_reset(self):
        reset = str(int((self.clock[0] + 90) * 1000))
        post = linear.http('k', opener=self.opener(Resp(b'{"data": {"ok": 1}}', {
            'X-RateLimit-Requests-Remaining': '7', 'X-RateLimit-Requests-Reset': reset,
            'X-RateLimit-Complexity-Remaining': '0', 'X-RateLimit-Complexity-Reset': reset})))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(post('q', {}), {'ok': 1})            # this answer still counts
            with self.assertRaises(linear.RateLimited):
                post('q', {})
        self.assertEqual(len(self.sent), 1)

    def test_budget_left_never_waits(self):
        good = lambda: Resp(b'{"data": {"ok": 1}}', {'X-RateLimit-Requests-Remaining': '900',
                                                    'X-RateLimit-Requests-Reset': '1'})
        post = linear.http('k', opener=self.opener(good(), good()))
        self.assertEqual([post('q', {}), post('q', {})], [{'ok': 1}, {'ok': 1}])

    def test_429_without_a_time_doubles_per_strike(self):
        post = linear.http('k', opener=self.opener(self.limited()))
        waits = []
        with contextlib.redirect_stderr(io.StringIO()):
            for _ in range(3):
                with self.assertRaises(linear.RateLimited) as hit:
                    post('q', {})
                waits.append(hit.exception.until - self.clock[0])
                self.clock[0] = hit.exception.until + 1
        self.assertEqual(waits, [60, 120, 240])


class SharedReads(unittest.TestCase):
    setUp, cli = flow.LinearBoardFlow.setUp, flow.LinearBoardFlow.cli

    def scoped(self, *scopes, extra=()):
        cfg = json.loads((self.repo/'.mstack/stack.json').read_text())
        cfg['taskboard']['orchestrators'] = {s: {'apps': ['*']} for s in scopes + tuple(extra)}
        (self.repo/'.mstack/stack.json').write_text(json.dumps(cfg))
        for s in scopes:
            self.cli('orchestrators', 'register', '--project', 'repo', '--scope', s, '--session', 'local_' + s)
        self.reads = []
        post = self.fake.post
        self.fake.post = lambda q, v: (self.reads.append(q) if 'issues(' in q else None) or post(q, v)

    def hold_hub(self):
        lock = open(cli.STATE.with_name('watch.hub.lock'), 'w')
        fcntl.flock(lock, fcntl.LOCK_EX)
        self.addCleanup(lock.close)

    def test_hub_reads_each_board_once_per_tick_for_all_its_scopes(self):
        self.scoped('one', 'two', 'three')
        task = self.cli('plan', '--project', 'repo', '--scope', 'one', '--title', 'T', '--plan', '-', stdin='p')['task']
        self.reads.clear()
        tick = self.cli('tick', '--hub')
        self.assertEqual(len(self.reads), 1)                      # signals, poll, dispatch and mirror of 3 scopes
        self.assertIn('MST', tick['linear_calls'])
        self.cli('tick', '--hub')
        self.assertEqual(len(self.reads), 1)                      # within LINEAR_EVERY: one timestamp per board
        self.assertEqual(list(json.loads(cli.STATE.read_text())['last_linear_poll']), ['repo'])
        self.fake.comment(task, '👍')
        with patch.object(cli, 'LINEAR_EVERY', 0):
            tick = self.cli('tick', '--hub')
        self.assertEqual([v['now'] for v in tick['verdicts']], ['Todo'])
        self.assertEqual(self.fake.state_of(task), 'started')     # dispatch saw the approval: a write refetches

    def test_scope_watcher_leaves_linear_to_a_running_hub(self):
        self.scoped('one', extra=['unregistered'])
        with patch.object(cli, 'LINEAR_EVERY', 0):
            self.cli('tick', '--project', 'repo', '--scope', 'one')
            self.assertEqual(len(self.reads), 1)                  # no hub: the scope watcher polls (fallback)
            self.hold_hub()
            self.reads.clear()
            tick = self.cli('tick', '--project', 'repo', '--scope', 'one')
            self.assertEqual((self.reads, tick['left_to_hub']), ([], ['repo']))
            self.cli('tick', '--hub')
            self.assertEqual(len(self.reads), 1)                  # the hub itself still reads
            self.reads.clear()
            self.cli('tick', '--project', 'repo', '--scope', 'unregistered')
            self.assertEqual(len(self.reads), 1)                  # a scope the hub doesn't tick keeps polling

    def test_rate_limit_skips_the_board_without_failing_the_tick(self):
        self.scoped('one')
        post = self.fake.post

        def limited(q, v):
            raise linear.RateLimited(2_000_000_000.0, 'kid')
        self.fake.post = limited
        with patch.object(cli, 'LINEAR_EVERY', 0):
            tick = self.cli('tick', '--hub')
        self.assertEqual(tick['rate_limited'], {'repo': 2_000_000_000.0})
        self.assertNotIn('tick_errors', tick)
        logged = {}
        first = cli.rate_note(tick['rate_limited'], logged)
        self.assertIn('rate-limited until', first)
        self.assertEqual(cli.rate_note(tick['rate_limited'], logged), '')   # logged once, not every tick
        self.fake.post = post
        self.assertEqual(cli.rate_note({}, logged), '')
        self.assertEqual(logged, {})
