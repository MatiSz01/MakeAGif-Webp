# Compilar MakeAGIF v3.1.1 para macOS (Apple Silicon)

## Sin Mac: GitHub Actions (recomendado)

Si no tenés una Mac, podés compilar en la nube igual que otros proyectos tuyos (Premiere Clip Hack, etc.):

1. Subí la carpeta **`MakeAGif-Webp`** como repositorio en GitHub (la raíz del repo debe contener `V3/` y `.github/workflows/build.yml`).
2. En GitHub: **Actions** → workflow **Build MakeAGIF** → **Run workflow** (manual), o hacé push a `main`/`master` con cambios en `V3/`.
3. Cuando termine (~15–25 min la primera vez), abrí el run y en **Artifacts** descargá `MakeAGIF-v3.1.1-macOS-arm64` (ZIP con `MakeAGIF v3.1.1.app`).

El `.exe` de Windows seguís compilándolo en tu PC con `MakeAGIF_v3.1.1_win.spec` (o el spec 3.1 clásico).

El workflow instala **ffmpeg**, **gifski** e **ImageMagick** (`magick`) en el runner — el mismo conjunto que el `.exe` de Windows (`tools/ffmpeg.exe`, `ffprobe.exe`, `gifski.exe`, `magick.exe`). No hace falta commitear los binarios de `tools/`.

**Monorepo:** si tu git root es `_PERSONAL_TOOLS` (padre de `MakeAGif-Webp`), editá en `.github/workflows/build.yml` la variable `V3_DIR`:

```yaml
env:
  V3_DIR: MakeAGif-Webp/V3
```

y mové el workflow a la raíz del monorepo: `_PERSONAL_TOOLS/.github/workflows/makeagif-build.yml`.

**Gatekeeper:** el `.app` de CI no está firmado; en la Mac destino: clic derecho → **Abrir** la primera vez.

---

## ¿Es posible?

**Sí**, y el código **ya es multiplataforma** (mismos `.py` que en Windows: rutas `tools/`, `open`, sin `.exe` en Mac). Lo que **no** se puede hacer es generar el `.app` desde tu PC Windows: PyInstaller **no** cross-compila a macOS. El build se hace **en una Mac** con chip M1/M2/M3 (o Intel con Rosetta si cambiás el spec a `x86_64`).

| Enfoque | Resultado |
|---------|-----------|
| Un solo `.py` | `MakeAGIF_v3.1.1_DND_Prototype.py` — no hace falta otro fuente solo para Mac |
| Un solo spec multi-OS | No recomendado; conviene **spec aparte** (`MakeAGIF_v3.1.1_mac.spec` vs `_win.spec`) |
| Ejecutable Windows | `MakeAGIF_v3.1.1_win.spec` (cuando lo dupliques desde 3.1) en Windows |
| App macOS arm64 | `MakeAGIF_v3.1.1_mac.spec` en Mac |

## Requisitos en la Mac

1. **macOS** en Apple Silicon (arm64).
2. **Python 3.11+** nativo arm64 (`python3 -c "import platform; print(platform.machine())"` → `arm64`).
3. Carpeta **`V3/tools/`** con `ffmpeg`, `ffprobe`, `gifski`, `magick` (o `./ci_bundle_mac_tools.sh`).
4. Opcional: `MakeAGIF.ico` (`python3 _make_icon.py` si tenés el PNG fuente).
5. Opcional: `MakeAGIF.icns` para icono en Finder (`./_make_icns_mac.sh`).

## Build rápido

```bash
cd V3
chmod +x build_mac_arm64.sh
./build_mac_arm64.sh
```

Salida: **`dist/MakeAGIF v3.1.1.app`**

Prueba:

```bash
open "dist/MakeAGIF v3.1.1.app"
```

## Primera apertura y Gatekeeper

Sin firma Apple, macOS puede bloquear la app. Para uso personal: **clic derecho → Abrir**. Para distribuir a otros: **codesign** + **notarization** (cuenta de desarrollador Apple).

## Diferencias vs el .exe de Windows

| | Windows | macOS |
|---|---------|--------|
| Formato | Un solo `.exe` (onefile) | `.app` (carpeta, onedir + BUNDLE) |
| Tools | `ffmpeg.exe`, `ffprobe.exe`, `gifski.exe`, `magick.exe` | `ffmpeg`, `ffprobe`, `gifski`, `magick` (sin extensión) |
| Drag & drop en icono | — | `argv_emulation=True` en el spec |
| Build desde | Tu PC actual | Solo en Mac |

## Versión 3.1 sin cambios

`MakeAGIF_v3.1_DND_Prototype.py` y `MakeAGIF_v3.1_mac.spec` siguen apuntando a **v3.1** por si querés el build “clásico” sin el trim async de **v3.1.1**.

## Problemas frecuentes

- **“ffmpeg not found”** → faltan binarios en `tools/` o no tienen `chmod +x`.
- **WebP con alpha distinto a Windows** → falta `tools/magick`; volvé a compilar con `./ci_bundle_mac_tools.sh` o el workflow actualizado.
- **App no abre / se cierra** → ejecutar desde Terminal para ver errores:
  `"dist/MakeAGIF v3.1.1.app/Contents/MacOS/MakeAGIF v3.1.1"`
- **Preview de vídeo negro** → instalar en la Mac los codecs/Qt que use el sistema; a veces hace falta probar con otro clip H.264.
