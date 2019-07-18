import pytest
from unittest.mock import patch

from pycloud import Event, CloudFileNotFoundError, CloudTemporaryError


@pytest.fixture
def gdrive():
    return 'a'


@pytest.fixture
def dropbox():
    return 'b'


@pytest.fixture(params=['gdrive', 'dropbox'])
def provider(request, gdrive, dropbox):
    return {'gdrive': gdrive, 'b': dropbox}[request.param]


@pytest.fixture
def env():
    return None


def test_connect(provider):
    assert provider.connected

# todo: should work with file-likes rather than path. Should it do it magically?


def test_upload(env, provider):
    temp = env.temp_file(fill_bytes=32)

    hash0 = provider.local_hash(temp)

    info1 = provider.upload(temp, "/dest")

    info2 = provider.upload(temp, "/dest", cloud_id=info1.cloud_id)

    assert info1.cloud_id == info2.cloud_id
    assert info1.hash == hash0
    assert info1.hash == info2.hash

    assert provider.exists("/dest")

    info3 = provider.download("/dest", temp)

    assert info1.cloud_id == info3.cloud_id

    assert info1.hash == info3.hash


def test_walk(env, provider):
    temp = env.temp_file(fill_bytes=32)
    info = provider.upload(temp, "/dest")
    assert not provider.walked

    for e in provider.events(timeout=1):
        if e is None:
            break
        assert provider.walked
        assert e.path == "/dest"
        assert e.cloud_id == info.cloud_id
        assert e.mtime
        assert e.exists
        assert e.source == Event.REMOTE


def test_event_basic(env, provider):
    for e in provider.events(timeout=1):
        if e is None:
            break
        assert False, "no events here!"

    assert provider.walked

    temp = env.temp_file(fill_bytes=32)
    info1 = provider.upload(temp, "/dest")
    assert info1 is not None  # TODO: check info1 for more things

    received_event = None
    for e in provider.events(timeout=1):
        if e is None:
            break
        received_event = e

    assert received_event is not None
    assert received_event.path == "/dest"
    assert received_event.cloud_id
    assert received_event.mtime
    assert received_event.exists
    assert received_event.source == Event.REMOTE
    provider.delete(cloud_id=received_event.cloud_id)
    with pytest.raises(CloudFileNotFoundError):
        provider.delete(cloud_id=received_event.cloud_id)

    received_event = None
    for e in provider.events(timeout=1):
        if e is None:
            break
        received_event = e

    assert received_event is not None
    assert received_event.path == "/dest"
    assert received_event.cloud_id
    assert received_event.mtime
    assert not received_event.exists
    assert received_event.source == Event.REMOTE


def test_api_failure(provider):
    # assert that the cloud 
    # a) uses an api function
    # b) does not trap CloudTemporaryError's

    def side_effect(*a, **k):
        raise CloudTemporaryError("fake disconned")

    with patch.object(provider, "api", side_effect=side_effect):
        with pytest.raises(CloudTemporaryError):
            provider.exists("/notexists")
