#!/bin/bash
# Kit do Diario de Itupeva. Uso: KIT=/tmp/kit bash setup.sh [voz]
set -e
K=${KIT:-/tmp/kit}; cd "$K"
[ -d osf ] || git clone --depth 1 -q https://github.com/marcologous/Open-Sauce-Fonts.git osf
[ -f logo.png ] || [ ! -f logo_base64.txt ] || python3 -c "import base64;open('logo.png','wb').write(base64.b64decode(open('logo_base64.txt').read().strip()))"
python3 -c "import PIL" 2>/dev/null || pip install -q --break-system-packages pillow
if [ "$1" = "voz" ]; then
  python3 -c "import onnxruntime" 2>/dev/null || pip install -q --break-system-packages onnxruntime numpy
  if [ ! -x espinst/bin/espeak-ng ]; then
    [ -d esp ] || git clone --depth 1 -q https://github.com/espeak-ng/espeak-ng.git esp
    cmake -S esp -B esp/build -DCMAKE_BUILD_TYPE=Release -DUSE_ASYNC=OFF -DUSE_MBROLA=OFF -DUSE_LIBSONIC=OFF -DUSE_LIBPCAUDIO=OFF -DUSE_SPEECHPLAYER=OFF -DCMAKE_INSTALL_PREFIX="$K/espinst" >/dev/null
    cmake --build esp/build -j8 >/dev/null && cmake --install esp/build >/dev/null
  fi
  if [ ! -d voz/vits-piper-pt_BR-faber-medium ]; then
    mkdir -p voz && curl -sSL -o voz/faber.tar.bz2 https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-pt_BR-faber-medium.tar.bz2
    tar xjf voz/faber.tar.bz2 -C voz
  fi
fi
echo "kit pronto em $K"
