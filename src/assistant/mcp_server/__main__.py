import asyncio
import sys
import warnings


def _setup_windows_event_loop() -> None:
    if sys.platform != "win32":
        return

    policy_cls = (
        getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
        or getattr(asyncio, "_WindowsSelectorEventLoopPolicy", None)
    )
    if policy_cls is None:
        return

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(policy_cls())


_setup_windows_event_loop()


from .server import main


if __name__ == "__main__":
    main()