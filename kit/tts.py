"""Piper (pt_BR faber) text-to-speech using espeak-ng CLI for phonemes and onnxruntime."""
import json, os, re, subprocess, sys, wave
import numpy as np
import onnxruntime as ort

KIT = os.environ.get("KIT", "/tmp/kit")
VOICE = KIT + "/voz/vits-piper-pt_BR-faber-medium/pt_BR-faber-medium"
ESPEAK = KIT + "/espinst/bin/espeak-ng"
os.environ["ESPEAK_DATA_PATH"] = KIT + "/espinst/share/espeak-ng-data"

cfg = json.load(open(VOICE + ".onnx.json"))
idmap = cfg["phoneme_id_map"]
sess = ort.InferenceSession(VOICE + ".onnx")
SR = cfg["audio"]["sample_rate"]


def phonemize(text):
    out = []
    for chunk, punct in re.findall(r"([^.,;:!?]+)([.,;:!?]?)", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        ipa = subprocess.run([ESPEAK, "-q", "-v", "pt-br", "--ipa"], input=chunk,
                             capture_output=True, text=True).stdout
        ipa = " ".join(ipa.split())
        out.append(ipa + (punct or ""))
    return " ".join(out)


def ids_for(ph):
    ids = idmap["^"] + idmap["_"]
    for ch in ph:
        if ch in idmap:
            ids += idmap[ch] + idmap["_"]
    return ids + idmap["$"]


def synth(text, path, length_scale=1.0):
    ids = np.array([ids_for(phonemize(text))], dtype=np.int64)
    inputs = {
        "input": ids,
        "input_lengths": np.array([ids.shape[1]], dtype=np.int64),
        "scales": np.array([0.667, length_scale, 0.8], dtype=np.float32),
    }
    audio = sess.run(None, inputs)[0].squeeze()
    audio = np.clip(audio / max(0.01, np.abs(audio).max()) * 0.9, -1, 1)
    pcm = (audio * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    return len(pcm) / SR


if __name__ == "__main__":
    print(synth(sys.argv[1], sys.argv[2]))
