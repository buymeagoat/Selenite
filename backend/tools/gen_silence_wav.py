import argparse
import wave
import struct


def gen_silence_wav(path: str, duration: float = 1.0, rate: int = 16000, channels: int = 1):
    nframes = int(duration * rate)
    sampwidth = 2  # 16-bit
    amplitude = 0

    with wave.open(path, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        for _ in range(nframes):
            for _c in range(channels):
                wf.writeframesraw(struct.pack('<h', amplitude))
        wf.writeframes(b'')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', required=True)
    parser.add_argument('-d', '--duration', type=float, default=1.0)
    parser.add_argument('-r', '--rate', type=int, default=16000)
    args = parser.parse_args()
    gen_silence_wav(args.output, duration=args.duration, rate=args.rate)
    print(f"Wrote {args.output}")
