"""What the deployment artefact must not quietly decide for itself.

`test_facts.py` does this for the landing page - asserts a fact about the
repository that no running code can supply. Same idea here, for the
Dockerfile: the image is where a setting can be baked in once and then
silently override everything a deployment configures at runtime, with no
error and nothing in a log to read.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "Dockerfile"
TEMPLATE = ROOT / "deploy" / "template.yaml"


def test_the_image_does_not_bake_in_ephemeral_keys():
    """The one that would undo secrets.py without saying so.

    `gateway._root_keypair()` checks POCKETCHANGE_EPHEMERAL_KEYS before it
    checks whether Secrets Manager is configured. An image that sets the flag
    therefore wins over any POCKETCHANGE_KEY_SECRET_NAME the deployment
    passes, every instance mints its own root key, and tokens signed by one
    instance fail verification on another - which looks like forgery, not
    like a misconfiguration. It was set here once, for reasons that were
    right before the secret existed.
    """
    body = DOCKERFILE.read_text()
    setting = [
        line.strip()
        for line in body.splitlines()
        # A comment explaining why it is absent is the point, not a violation.
        if "POCKETCHANGE_EPHEMERAL_KEYS" in line and not line.strip().startswith("#")
    ]
    assert not setting, (
        "the Dockerfile sets POCKETCHANGE_EPHEMERAL_KEYS, which takes "
        f"precedence over Secrets Manager in gateway._root_keypair(): {setting}"
    )


def test_the_image_does_not_bake_in_a_dotenv_exception():
    """POCKETCHANGE_NO_DOTENV must stay ON in the image.

    The inverse of the test above: this one is required to be set, because a
    .env file reaching a deployed container is a credential arriving from
    somewhere nobody configured.
    """
    assert re.search(r"^\s*POCKETCHANGE_NO_DOTENV=1", DOCKERFILE.read_text(), re.M)


def test_the_policies_are_copied_into_the_image():
    """cedar.decide fails CLOSED when it cannot read a policy, so an image
    built without the policy set answers 503 to every payment. The Dockerfile
    says so in a comment; this is the version that fails a build.
    """
    assert re.search(r"^COPY policies/", DOCKERFILE.read_text(), re.M)


def test_the_template_port_matches_the_image_port():
    """App Runner routes to one port and the container listens on one port.
    Disagreeing is a health check that never passes and a service that never
    goes live, for a reason neither file states on its own.
    """
    image_port = re.search(r"^ENV PORT=(\d+)", DOCKERFILE.read_text(), re.M)
    assert image_port, "the Dockerfile no longer states a default PORT"
    assert f"Port: '{image_port.group(1)}'" in TEMPLATE.read_text(), (
        f"deploy/template.yaml does not route to port {image_port.group(1)}"
    )
