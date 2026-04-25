"""
Dataset preprocessor: auto-detects and crops faces from raw dataset images.

Usage:
  python training/preprocess.py --src /path/to/raw --dst training/data --label real
  python training/preprocess.py --src /path/to/spoof_raw --dst training/data --label spoof
"""
import argparse
import os
import cv2
import mediapipe as mp
from pathlib import Path

mp_fd = mp.solutions.face_detection


def crop_face_mp(img, detector, padding=0.2):
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    res = detector.process(rgb)
    if not res.detections:
        return None
    bb = res.detections[0].location_data.relative_bounding_box
    x = int(max(0, (bb.xmin - bb.width * padding)) * w)
    y = int(max(0, (bb.ymin - bb.height * padding)) * h)
    x2 = int(min(w, (bb.xmin + bb.width * (1 + padding)) * w))
    y2 = int(min(h, (bb.ymin + bb.height * (1 + padding)) * h))
    roi = img[y:y2, x:x2]
    return roi if roi.size > 0 else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src',   required=True, help='Source directory with raw images')
    parser.add_argument('--dst',   default='training/data', help='Output base directory')
    parser.add_argument('--label', required=True, choices=['real', 'spoof'])
    parser.add_argument('--size',  default=224, type=int, help='Output image size')
    parser.add_argument('--limit', default=0,   type=int, help='Max images (0 = all)')
    args = parser.parse_args()

    out_dir = Path(args.dst) / args.label
    out_dir.mkdir(parents=True, exist_ok=True)

    exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    files = [f for f in Path(args.src).rglob('*') if f.suffix.lower() in exts]
    if args.limit > 0:
        files = files[:args.limit]

    print(f"Processing {len(files)} images → {out_dir}")
    saved = skipped = 0

    with mp_fd.FaceDetection(model_selection=0, min_detection_confidence=0.4) as det:
        for i, fp in enumerate(files):
            img = cv2.imread(str(fp))
            if img is None:
                skipped += 1; continue

            face = crop_face_mp(img, det)
            if face is None:
                # fall back: use the whole image (resized)
                face = img

            face_resized = cv2.resize(face, (args.size, args.size))
            out_path = out_dir / f"{args.label}_{i:06d}.jpg"
            cv2.imwrite(str(out_path), face_resized, [cv2.IMWRITE_JPEG_QUALITY, 92])
            saved += 1

            if (i + 1) % 100 == 0:
                print(f"  [{i+1}/{len(files)}] saved={saved} skipped={skipped}")

    print(f"\n✅ Done. Saved: {saved} | Skipped: {skipped}")


if __name__ == '__main__':
    main()
