"""Control whether Whisp starts at login, via a per-user LaunchAgent.

Enabling writes and loads the agent (start now + at every login, relaunch on
crash). Disabling removes the agent so it won't start next login, but does NOT
kill the currently running app (that would yank the menu bar out from under the
user); the app keeps running until they quit it."""
import os
import subprocess

LABEL = "com.usama.whisp"
_PLIST = os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
_APP_BIN = "/Applications/Whisp.app/Contents/MacOS/Whisp"

_PLIST_BODY = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array><string>{_APP_BIN}</string></array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
    <key>ProcessType</key><string>Interactive</string>
</dict>
</plist>
"""


def is_enabled() -> bool:
    return os.path.exists(_PLIST)


def enable() -> None:
    try:
        os.makedirs(os.path.dirname(_PLIST), exist_ok=True)
        with open(_PLIST, "w") as f:
            f.write(_PLIST_BODY)
        uid = os.getuid()
        subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", _PLIST],
                       capture_output=True, timeout=8)
    except Exception:
        pass


def disable() -> None:
    # Remove the agent so it won't start next login. Do NOT bootout the running
    # service (that would terminate this very app). It exits when the user quits.
    try:
        if os.path.exists(_PLIST):
            os.remove(_PLIST)
        uid = os.getuid()
        subprocess.run(["launchctl", "disable", f"gui/{uid}/{LABEL}"],
                       capture_output=True, timeout=8)
    except Exception:
        pass
