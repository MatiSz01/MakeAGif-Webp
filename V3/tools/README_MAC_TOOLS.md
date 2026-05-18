# macOS (Apple Silicon) — herramientas en `tools/`

Antes de compilar con `build_mac_arm64.sh`, esta carpeta debe tener binarios **arm64** **sin** extensión `.exe`:

| Archivo   | Obligatorio | Notas |
|-----------|-------------|--------|
| `ffmpeg`  | Sí          | `chmod +x` |
| `ffprobe` | Sí          | suele venir con ffmpeg |
| `gifski`  | Sí          | universal/arm64 desde [gif.ski](https://gif.ski/) |
| `magick`  | No          | ImageMagick, opcional |

## No mezclar con Windows

En un repo compartido, los `.exe` de Windows **no** sirven en Mac. Opciones:

1. En la Mac, vaciar o reemplazar `tools/` solo antes del build (no commitear los binarios si pesan mucho).
2. Mantener `tools_win/` y `tools_mac/` locales y copiar a `tools/` según la plataforma.

## Fuentes habituales

- **ffmpeg / ffprobe**: builds arm64 en [evermeet.cx/ffmpeg](https://evermeet.cx/ffmpeg/) (descargar, renombrar, `chmod +x`).
- **gifski**: release macOS en GitHub del proyecto gif.ski.

Verificar:

```bash
file tools/ffmpeg
# … arm64 …
chmod +x tools/ffmpeg tools/ffprobe tools/gifski
./tools/ffmpeg -version
```
