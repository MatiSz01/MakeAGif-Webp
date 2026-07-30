================================================================
  MakeAGIF v3.1.10 — CÓMO INSTALAR EN macOS
================================================================


OPCIÓN A — La más fácil (recomendada)
--------------------------------------
1. Arrastrá "MakeAGIF v3.1.10.app" a la carpeta
   Aplicaciones (Applications).
2. Hacé doble click en "Open MakeAGIF (first run).command"
   (este archivo, incluido en este mismo zip).
3. Si aparece un aviso de que no se puede verificar el desarrollador:
   click derecho sobre el archivo .command -> Abrir -> Abrir.
4. Se abre una ventana de Terminal que hace todo el trabajo sola
   y al final abre MakeAGIF. Las próximas veces abrís la app
   normalmente desde Aplicaciones o Launchpad.


OPCIÓN B — Manual, por Terminal
---------------------------------
1. Arrastrá "MakeAGIF v3.1.10.app" a la carpeta
   Aplicaciones.
2. Abrí la app "Terminal" (Cmd+Espacio, escribí "Terminal", Enter).
3. Pegá esta línea y presioná Enter:

   xattr -cr "/Applications/MakeAGIF v3.1.10.app"

4. Abrí la app normalmente desde Aplicaciones o Launchpad.


Si todavía no abre
--------------------
- Click derecho sobre la app -> Abrir -> confirmá "Abrir" de nuevo.
- O andá a: Ajustes del Sistema -> Privacidad y Seguridad -> bajá
  hasta el aviso sobre "MakeAGIF" -> "Abrir de todas formas".


¿Qué tiene adentro la app?
----------------------------
MakeAGIF incluye sus propias copias de estas herramientas CLI (arm64),
así que no necesitás instalar nada más:
  - ffmpeg + ffprobe  (decodificación de video)
  - gifski            (codificador GIF de alta calidad)
  - img2webp          (codificador WebP, libwebp)
  - magick            (ImageMagick, rutas alternativas)

Simplemente arrastrá un video a la ventana, elegí GIF o WebP,
ajustá los settings y hacé clic en Convert.


¿Dónde se guardan mis settings?
--------------------------------
En macOS, tus settings y presets viven en:
   ~/Library/Application Support/MakeAGIF/
