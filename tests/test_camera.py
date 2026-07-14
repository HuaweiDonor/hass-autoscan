import itertools

from app.camera import FrameReader


class FakeCapture:
    def __init__(self, opened, reads):
        self._opened = opened
        self._reads = list(reads)
        self.released = False

    def isOpened(self):
        return self._opened

    def read(self):
        if self._reads:
            return self._reads.pop(0)
        return (False, None)

    def release(self):
        self.released = True


def make_factory(*captures):
    captures = list(captures)

    def factory():
        return captures.pop(0)

    return factory


def test_yields_frames_from_successful_reads():
    capture = FakeCapture(opened=True, reads=[(True, "frame1"), (True, "frame2")])
    reader = FrameReader(
        capture_factory=make_factory(capture),
        sample_fps=10,
        sleep=lambda s: None,
    )

    frames = list(itertools.islice(reader.frames(), 2))

    assert frames == ["frame1", "frame2"]


def test_reconnects_when_capture_fails_to_open():
    bad_capture = FakeCapture(opened=False, reads=[])
    good_capture = FakeCapture(opened=True, reads=[(True, "frame1")])
    sleeps = []
    reader = FrameReader(
        capture_factory=make_factory(bad_capture, good_capture),
        sample_fps=10,
        sleep=lambda s: sleeps.append(s),
        initial_backoff_seconds=1,
    )

    frames = list(itertools.islice(reader.frames(), 1))

    assert frames == ["frame1"]
    assert bad_capture.released is True
    assert sleeps[0] == 1  # backoff sleep happened before reconnect


def test_reconnects_when_read_returns_false():
    dropped_capture = FakeCapture(opened=True, reads=[(True, "frame1"), (False, None)])
    recovered_capture = FakeCapture(opened=True, reads=[(True, "frame2")])
    reader = FrameReader(
        capture_factory=make_factory(dropped_capture, recovered_capture),
        sample_fps=10,
        sleep=lambda s: None,
    )

    frames = list(itertools.islice(reader.frames(), 2))

    assert frames == ["frame1", "frame2"]
    assert dropped_capture.released is True


def test_backoff_increases_exponentially_and_caps():
    captures = [FakeCapture(opened=False, reads=[]) for _ in range(4)]
    captures.append(FakeCapture(opened=True, reads=[(True, "frame1")]))
    sleeps = []
    reader = FrameReader(
        capture_factory=make_factory(*captures),
        sample_fps=10,
        sleep=lambda s: sleeps.append(s),
        initial_backoff_seconds=1,
        max_backoff_seconds=6,
    )

    list(itertools.islice(reader.frames(), 1))

    assert sleeps == [1, 2, 4, 6]


def test_backoff_resets_after_successful_read():
    captures = [FakeCapture(opened=False, reads=[])]
    captures.append(
        FakeCapture(opened=True, reads=[(True, "frame1"), (False, None)])
    )
    captures.append(FakeCapture(opened=True, reads=[(True, "frame2")]))
    sleeps = []
    reader = FrameReader(
        capture_factory=make_factory(*captures),
        sample_fps=10,
        sleep=lambda s: sleeps.append(s),
        initial_backoff_seconds=1,
        max_backoff_seconds=30,
    )

    frames = list(itertools.islice(reader.frames(), 2))

    assert frames == ["frame1", "frame2"]
    # first backoff (open failure) = 1, then after a successful read the
    # backoff counter resets, so the next failure's backoff is 1 again,
    # not 2. (0.1 = throttle sleep at sample_fps=10, not a backoff sleep)
    backoff_sleeps = [s for s in sleeps if s != 0.1]
    assert backoff_sleeps == [1, 1]


def test_throttles_between_frames_at_sample_fps():
    capture = FakeCapture(opened=True, reads=[(True, "frame1"), (True, "frame2")])
    sleeps = []
    reader = FrameReader(
        capture_factory=make_factory(capture),
        sample_fps=2,
        sleep=lambda s: sleeps.append(s),
    )

    list(itertools.islice(reader.frames(), 2))

    assert 0.5 in sleeps
