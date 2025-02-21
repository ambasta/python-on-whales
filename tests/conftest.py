import tempfile
import time
from pathlib import Path

import pydantic
import pytest

from python_on_whales import docker


@pytest.fixture
def docker_registry():
    yield from _docker_registry()


@pytest.fixture
def docker_registry_without_login():
    yield from _docker_registry(login=False)


def _docker_registry(login=True):
    encrypted_password = docker.run(
        "mhenry07/apache2-utils",
        ["htpasswd", "-Bbn", "my_user", "my_password"],
        remove=True,
    )
    with tempfile.TemporaryDirectory() as tmp_path:
        tmp_path = Path(tmp_path)
        htpasswd_file = tmp_path / "htpasswd"
        htpasswd_file.write_text(encrypted_password)
        registry = docker.container.create(
            "registry:2",
            remove=True,
            envs=dict(
                REGISTRY_AUTH="htpasswd",
                REGISTRY_AUTH_HTPASSWD_REALM="Registry Realm",
                REGISTRY_AUTH_HTPASSWD_PATH="/tmp/htpasswd",
            ),
            publish=[(5000, 5000)],
        )
        with registry:
            registry.copy_to(htpasswd_file, "/tmp/htpasswd")
            registry.start()
            time.sleep(1.5)
            if login:
                docker.login(
                    "localhost:5000", username="my_user", password="my_password"
                )
            yield "localhost:5000"


@pytest.fixture
def swarm_mode():
    docker.swarm.init()
    yield
    docker.swarm.leave(force=True)
    time.sleep(1)


def pytest_collection_modifyitems(config, items):
    if pydantic.__version__.startswith("1"):
        return
    for item in items:
        item.add_marker(
            pytest.mark.filterwarnings("error::pydantic.PydanticDeprecatedSince20")
        )
