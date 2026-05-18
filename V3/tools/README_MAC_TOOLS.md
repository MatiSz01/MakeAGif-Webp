# macOS (Apple Silicon) — herramientas en `tools/`

Debe coincidir con el bundle de **Windows** (`ffmpeg`, `ffprobe`, `gifski`, `magick`).

| Archivo   | Obligatorio | Rol |
|-----------|-------------|-----|
| `ffmpeg`  | Sí          | Extracción de frames, WebP, escenas |
| `ffprobe` | Sí          | Metadatos / VFR |
| `gifski`  | Sí          | Encode GIF |
| `magick`  | Sí          | WebP con transparencia (alpha) — ImageMagick 7 |

Todos **arm64**, **sin** `.exe`, con `chmod +x`.

## Instalación automática (Mac o CI)

Desde `V3/`:

```bash
chmod +x ci_bundle_mac_tools.sh
./ci_bundle_mac_tools.sh
```

## Manual

```bash
brew install ffmpeg gifski imagemagick
# luego copiar binarios a tools/ (ver ci_bundle_mac_tools.sh)
```

## No mezclar con Windows

Los `.exe` de Windows no sirven en Mac. Usá `tools/` solo con binarios Mac antes del build.
