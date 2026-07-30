================================================================
  MakeAGIF v3.1.10 — HOW TO INSTALL ON macOS
================================================================


OPTION A — Easiest (recommended)
-----------------------------------
1. Drag "MakeAGIF v3.1.10.app" into your
   Applications folder.
2. Double-click "Open MakeAGIF (first run).command"
   (included in this same zip).
3. If macOS warns it can't verify the developer of the script:
   right-click the .command file -> Open -> Open.
4. A Terminal window opens and does all the work automatically,
   then launches the app. From then on, open the app normally
   from Applications or Launchpad.


OPTION B — Manual, via Terminal
----------------------------------
1. Drag "MakeAGIF v3.1.10.app" into your
   Applications folder.
2. Open the "Terminal" app (Cmd+Space, type "Terminal", Enter).
3. Paste this line and press Enter:

   xattr -cr "/Applications/MakeAGIF v3.1.10.app"

4. Open the app normally from Applications or Launchpad.


If it still won't open
-------------------------
- Right-click the app -> Open -> confirm "Open" again.
- Or go to: System Settings -> Privacy & Security -> scroll down to
  the notice about "MakeAGIF" -> "Open Anyway".


What's inside the app?
------------------------
MakeAGIF bundles its own copies of these CLI tools (arm64), so you
don't need to install anything else:
  - ffmpeg + ffprobe  (video decoding)
  - gifski            (high-quality GIF encoder)
  - img2webp          (WebP encoder, libwebp)
  - magick            (ImageMagick, fallback paths)

Just drag a video onto the window, pick GIF or WebP, adjust the
settings and click Convert.


Where are my settings stored?
------------------------------
On macOS, your settings and presets live in:
   ~/Library/Application Support/MakeAGIF/
