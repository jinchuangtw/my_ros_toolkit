#!/usr/bin/env python3
import argparse
import os
import cv2


def parse_args():
    parser = argparse.ArgumentParser(description="Extract all frames from a video.")
    parser.add_argument("input_video", help="Input video file path.")
    parser.add_argument("output_folder", help="Output folder for extracted frames.")
    return parser.parse_args()


def main():
    args = parse_args()

    input_video = args.input_video
    output_folder = args.output_folder

    if not os.path.isfile(input_video):
        raise FileNotFoundError(f"Input video not found: {input_video}")

    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(input_video)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_video}")

    frame_idx = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        output_path = os.path.join(output_folder, f"frame_{frame_idx:06d}.png")
        success = cv2.imwrite(output_path, frame)

        if not success:
            raise RuntimeError(f"Failed to write frame: {output_path}")

        frame_idx += 1

    cap.release()

    print(f"[INFO] Input video : {input_video}")
    print(f"[INFO] Output dir  : {output_folder}")
    print(f"[INFO] Frames saved: {frame_idx}")


if __name__ == "__main__":
    main()
