#!/bin/bash
#
# MakeAGIF v3.1.10 — macOS first-run helper
# ==========================================
# This app is not signed with an Apple Developer certificate, so when you
# download it macOS marks it as "quarantined" and refuses to open it (it may
# bounce once in the Dock and disappear, or say it "cannot be opened").
#
# This script:
#   1. Optionally installs the app into /Applications.
#   2. Removes the Gatekeeper quarantine flag so it can launch.
#   3. Opens the app.
# You only need to run it ONCE. After that the app opens normally.
#
# How to use:  double-click this file. (If macOS blocks the script itself,
# right-click it -> Open -> Open.)
#
set +e

echo "────────────────────────────────────────────"
echo "  MakeAGIF v3.1.10 — first-run helper"
echo "────────────────────────────────────────────"
echo ""

# Folder this script lives in (works when double-clicked from Finder).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

APP_NAME="MakeAGIF v3.1.10.app"

SRC=""
# 1) App sitting next to this script (typical after unzipping the download).
if [ -d "$DIR/$APP_NAME" ]; then
    SRC="$DIR/$APP_NAME"
# 2) Common locations.
elif [ -d "$HOME/Downloads/$APP_NAME" ]; then
    SRC="$HOME/Downloads/$APP_NAME"
elif [ -d "/Applications/$APP_NAME" ]; then
    SRC="/Applications/$APP_NAME"
fi

# 3) Ask the user to drag the app in if we still can't find it.
if [ -z "$SRC" ]; then
    echo "Couldn't find $APP_NAME automatically."
    echo "Drag $APP_NAME onto this window and press Return:"
    read -r SRC
fi

# Trim trailing slash and surrounding quotes that a Finder drag may add.
SRC="${SRC%/}"
SRC="${SRC%\"}"
SRC="${SRC#\"}"

if [ ! -d "$SRC" ]; then
    echo ""
    echo "❌ Could not find the app at: $SRC"
    echo "   Make sure $APP_NAME is next to this script and try again."
    echo ""
    read -r -p "Press Return to close…" _
    exit 1
fi

echo "→ Found app:  $SRC"
echo ""

# ── Step 1: optionally install into /Applications ───────────────────────────
APP="$SRC"
DEST="/Applications/$APP_NAME"

if [ "$SRC" = "$DEST" ]; then
    echo "→ App is already installed in /Applications."
else
    printf "→ Install into /Applications? [Y/n]: "
    read -r REPLY
    case "$REPLY" in
        [Nn]*)
            echo "  Skipping install — will run it from its current location."
            ;;
        *)
            echo "  Copying to /Applications…"
            # Remove any older copy first so we don't merge two bundles.
            if [ -d "$DEST" ]; then
                rm -rf "$DEST" 2>/dev/null
                if [ -d "$DEST" ]; then
                    echo "  (need administrator permission to replace the existing copy)"
                    sudo rm -rf "$DEST"
                fi
            fi
            # ditto is the macOS-correct way to copy an .app bundle.
            ditto "$SRC" "$DEST" 2>/dev/null
            if [ ! -d "$DEST" ]; then
                echo "  (need administrator permission to write to /Applications)"
                sudo ditto "$SRC" "$DEST"
            fi
            if [ -d "$DEST" ]; then
                APP="$DEST"
                echo "  ✓ Installed to /Applications."
            else
                echo "  ⚠ Could not install to /Applications — running from $SRC instead."
            fi
            ;;
    esac
fi

echo ""
# ── Step 2: remove the quarantine flag ──────────────────────────────────────
echo "→ Removing the macOS quarantine flag…"
xattr -dr com.apple.quarantine "$APP" 2>/dev/null
# Clear any leftover provenance attributes that can also trip Gatekeeper.
xattr -cr "$APP" 2>/dev/null
echo "✓ Done."

echo ""
# ── Step 3: launch ──────────────────────────────────────────────────────────
echo "→ Launching MakeAGIF v3.1.10…"
open "$APP"
RESULT=$?

echo ""
if [ $RESULT -eq 0 ]; then
    echo "✓ The app should now be open. You can close this window."
    if [ "$APP" = "$DEST" ]; then
        echo "  It's in your Applications folder — open it from Launchpad or Finder next time."
    else
        echo "  From now on you can open the app by double-clicking it normally."
    fi
else
    echo "If it still doesn't open:"
    echo "  • Right-click $APP_NAME → Open → Open, OR"
    echo "  • System Settings → Privacy & Security → 'Open Anyway'."
fi
echo ""
read -r -p "Press Return to close…" _
