from django.apps import AppConfig


class ActionsConfig(AppConfig):
    name = 'actions'

    def ready(self):
        # Registers the receiver in actions/signals.py that listens for
        # devices.signals.change_request_poll_result. Must be imported
        # here (not at module top-level) so Django's app registry is
        # fully loaded before the signal-to-model wiring happens.
        import actions.signals  # noqa: F401