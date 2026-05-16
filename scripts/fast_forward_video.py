#!/usr/bin/env python3
import argparse
import os
import cv2


def format_speed_text(speed):
    """
    Convert speed number to clean display text.
    4.0 -> 4x
    2.5 -> 2.5x
    """
    if float(speed).is_integer():
        return f"{int(speed)}x"
    return f"{speed:g}x"


def add_watermark(
    frame,
    text,
    scale=1.2,
    thickness=2,
    margin=24,
):
    """
    Add a speed watermark at the bottom-right corner.
    """
    font = cv2.FONT_HERSHEY_SIMPLEX

    h, w = frame.shape[:2]

    text_size, baseline = cv2.getTextSize(
        text,
        font,
        scale,
        thickness,
    )

    text_w, text_h = text_size

    x = w - text_w - margin
    y = h - margin

    # Semi-readable outline / shadow
    cv2.putText(
        frame,
        text,
        (x + 2, y + 2),
        font,
        scale,
        (0, 0, 0),
        thickness + 2,
        cv2.LINE_AA,
    )

    # Main white text
    cv2.putText(
        frame,
        text,
        (x, y),
        font,
        scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA,
    )

    return frame


def fast_forward_drop_frames(
    input_path,
    output_path,
    speed,
    output_fps=None,
    codec="mp4v",
    watermark=False,
    watermark_text=None,
    watermark_scale=1.2,
    watermark_thickness=2,
    watermark_margin=24,
):
    """
    Fast forward by dropping frames.

    Example:
    input fps = 20, speed = 4
    output fps = 20
    output duration becomes roughly 1/4.
    """
    if speed <= 1.0:
        raise ValueError("--speed must be greater than 1.0 for fast forward.")

    cap = cv2.VideoCapture(input_path)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open input video: {input_path}")

    input_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if input_fps <= 0:
        input_fps = 30.0

    if output_fps is None:
        output_fps = input_fps

    if not os.path.splitext(output_path)[1]:
        output_path += ".mp4"

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(output_path, fourcc, output_fps, (width, height))

    if not writer.isOpened():
        raise RuntimeError(f"Cannot open output video: {output_path}")

    if watermark and watermark_text is None:
        watermark_text = format_speed_text(speed)

    out_idx = 0
    written = 0

    while True:
        src_idx = int(round(out_idx * speed))

        if src_idx >= total_frames:
            break

        cap.set(cv2.CAP_PROP_POS_FRAMES, src_idx)
        ret, frame = cap.read()

        if not ret:
            break

        if watermark:
            frame = add_watermark(
                frame,
                watermark_text,
                scale=watermark_scale,
                thickness=watermark_thickness,
                margin=watermark_margin,
            )

        writer.write(frame)
        written += 1
        out_idx += 1

        if written % 300 == 0:
            print(f"[INFO] wrote {written} frames")

    cap.release()
    writer.release()

    print("[DONE] Fast forward complete")
    print(f"       Input       : {input_path}")
    print(f"       Output      : {output_path}")
    print(f"       Speed       : {speed}x")
    print(f"       Input FPS   : {input_fps:.2f}")
    print(f"       Output FPS  : {output_fps:.2f}")
    print(f"       Input frames: {total_frames}")
    print(f"       Written     : {written}")
    print(f"       Watermark   : {watermark}")


def fast_forward_by_fps_metadata(
    input_path,
    output_path,
    speed,
    codec="mp4v",
    watermark=False,
    watermark_text=None,
    watermark_scale=1.2,
    watermark_thickness=2,
    watermark_margin=24,
):
    """
    Fast forward by writing all frames but increasing output FPS metadata.

    This preserves every frame, but output fps becomes input_fps * speed.
    Some presentation software may not like very high FPS, so the drop-frame
    method is usually safer for reports.
    """
    if speed <= 1.0:
        raise ValueError("--speed must be greater than 1.0 for fast forward.")

    cap = cv2.VideoCapture(input_path)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open input video: {input_path}")

    input_fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if input_fps <= 0:
        input_fps = 30.0

    output_fps = input_fps * speed

    if not os.path.splitext(output_path)[1]:
        output_path += ".mp4"

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(output_path, fourcc, output_fps, (width, height))

    if not writer.isOpened():
        raise RuntimeError(f"Cannot open output video: {output_path}")

    if watermark and watermark_text is None:
        watermark_text = format_speed_text(speed)

    written = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        if watermark:
            frame = add_watermark(
                frame,
                watermark_text,
                scale=watermark_scale,
                thickness=watermark_thickness,
                margin=watermark_margin,
            )

        writer.write(frame)
        written += 1

        if written % 500 == 0:
            print(f"[INFO] wrote {written} frames")

    cap.release()
    writer.release()

    print("[DONE] Fast forward complete")
    print(f"       Input      : {input_path}")
    print(f"       Output     : {output_path}")
    print(f"       Speed      : {speed}x")
    print(f"       Input FPS  : {input_fps:.2f}")
    print(f"       Output FPS : {output_fps:.2f}")
    print(f"       Frames     : {written}")
    print(f"       Watermark  : {watermark}")


def main():
    parser = argparse.ArgumentParser(
        description="Fast forward a video by a given speed factor."
    )

    parser.add_argument("--input", required=True, help="Input video path")
    parser.add_argument("--output", required=True, help="Output video path")
    parser.add_argument(
        "--speed",
        type=float,
        required=True,
        help="Fast forward speed, e.g. 2, 4, 8",
    )

    parser.add_argument(
        "--method",
        choices=["drop", "fps"],
        default="drop",
        help=(
            "drop: drop frames and keep normal fps, recommended for reports. "
            "fps: keep all frames but increase video fps metadata."
        ),
    )

    parser.add_argument(
        "--output-fps",
        type=float,
        default=None,
        help="Only used by --method drop. If not set, use input fps.",
    )

    parser.add_argument(
        "--codec",
        default="mp4v",
        help="OpenCV fourcc codec, e.g. mp4v, XVID, MJPG",
    )

    parser.add_argument(
        "--watermark",
        action="store_true",
        help="Add speed watermark at bottom-right corner, e.g. 4x.",
    )

    parser.add_argument(
        "--watermark-text",
        default=None,
        help="Custom watermark text. If not set, use speed text such as 4x.",
    )

    parser.add_argument(
        "--watermark-scale",
        type=float,
        default=1.2,
        help="Watermark font scale.",
    )

    parser.add_argument(
        "--watermark-thickness",
        type=int,
        default=2,
        help="Watermark font thickness.",
    )

    parser.add_argument(
        "--watermark-margin",
        type=int,
        default=24,
        help="Watermark margin from bottom-right corner in pixels.",
    )

    args = parser.parse_args()

    if args.method == "drop":
        fast_forward_drop_frames(
            input_path=args.input,
            output_path=args.output,
            speed=args.speed,
            output_fps=args.output_fps,
            codec=args.codec,
            watermark=args.watermark,
            watermark_text=args.watermark_text,
            watermark_scale=args.watermark_scale,
            watermark_thickness=args.watermark_thickness,
            watermark_margin=args.watermark_margin,
        )
    else:
        fast_forward_by_fps_metadata(
            input_path=args.input,
            output_path=args.output,
            speed=args.speed,
            codec=args.codec,
            watermark=args.watermark,
            watermark_text=args.watermark_text,
            watermark_scale=args.watermark_scale,
            watermark_thickness=args.watermark_thickness,
            watermark_margin=args.watermark_margin,
        )


if __name__ == "__main__":
    main()
