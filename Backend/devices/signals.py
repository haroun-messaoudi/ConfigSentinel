import django.dispatch

# Fired by pull_config_task after a poll triggered by a ChangeRequest.
# The actions app verifies requested commands against the read-back config.
change_request_poll_result = django.dispatch.Signal()
# providing_args (informational only, Django 4+ doesn't enforce this):
#   change_request_id: int
#   raw_config: str | None
#   error_message: str | None