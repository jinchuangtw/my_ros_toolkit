#!/usr/bin/env python3
import argparse
import os
import statistics

import cv2
import rosbag
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CompressedImage
import numpy as np


def msg_to_cv2(msg, bridge):
    """
    Convert ROS Image or CompressedImage to OpenCV BGR image.

    Some rosbag files dynamically generate message classes such as:
        tmposdojuvw._sensor_msgs__Image

    Therefore, do not rely on isinstance(msg, Image).
    Use msg._type instead.
    """
    msg_type = getattr(msg, "_type", "")

    if msg_type == "sensor_msgs/Image":
        return bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

    if msg_type == "sensor_msgs/CompressedImage":
        np_arr = np.frombuffer(msg.data, np.uint8)
        return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    raise TypeError(f"Unsupported message type: {msg_type}, python class: {type(msg)}")


def estimate_fps(bag_path, topic, max_samples=500):
    """
    Estimate fps from ROS timestamps using median dt.
    """
    stamps = []

    with rosbag.Bag(bag_path, "r") as bag:
        for _, msg, t in bag.read_messages(topics=[topic]):
            if hasattr(msg, "header") and msg.header.stamp.to_sec() > 0:
                stamps.append(msg.header.stamp.to_sec())
            else:
                stamps.append(t.to_sec())

            if len(stamps) >= max_samples:
                break

    if len(stamps) < 2:
        return None

    dts = [stamps[i + 1] - stamps[i] for i in range(len(stamps) - 1)]
    dts = [dt for dt in dts if dt > 0]

    if not dts:
        return None

    median_dt = statistics.median(dts)
    return 1.0 / median_dt


def get_first_frame_info(bag_path, topic, bridge):
    with rosbag.Bag(bag_path, "r") as bag:
        for _, msg, _ in bag.read_messages(topics=[topic]):
            frame = msg_to_cv2(msg, bridge)
            h, w = frame.shape[:2]
            return w, h

    return None, None


def convert_topic_to_video(
    bag_path,
    topic,
    output_path,
    fps=None,
    codec="mp4v",
    resize=None,
    start_time=None,
    duration=None,
):
    bridge = CvBridge()

    if fps is None:
        fps = estimate_fps(bag_path, topic)
        if fps is None:
            fps = 20.0
            print(
                f"[WARN] Could not estimate FPS for {topic}. Use default fps={fps:.2f}"
            )
        else:
            print(f"[INFO] Estimated FPS for {topic}: {fps:.2f}")

    first_w, first_h = get_first_frame_info(bag_path, topic, bridge)
    if first_w is None:
        print(f"[WARN] No frames found in topic: {topic}")
        return

    if resize is not None:
        out_w, out_h = resize
    else:
        out_w, out_h = first_w, first_h

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))

    if not writer.isOpened():
        raise RuntimeError(f"Cannot open video writer: {output_path}")

    frame_count = 0
    first_stamp = None

    with rosbag.Bag(bag_path, "r") as bag:
        for _, msg, t in bag.read_messages(topics=[topic]):
            if hasattr(msg, "header") and msg.header.stamp.to_sec() > 0:
                stamp = msg.header.stamp.to_sec()
            else:
                stamp = t.to_sec()

            if first_stamp is None:
                first_stamp = stamp

            rel_time = stamp - first_stamp

            if start_time is not None and rel_time < start_time:
                continue

            if duration is not None:
                if start_time is None:
                    end_time = duration
                else:
                    end_time = start_time + duration

                if rel_time > end_time:
                    break

            frame = msg_to_cv2(msg, bridge)

            if resize is not None:
                frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)

            writer.write(frame)
            frame_count += 1

            if frame_count % 500 == 0:
                print(f"[INFO] {topic}: wrote {frame_count} frames")

    writer.release()

    print(f"[DONE] {topic}")
    print(f"       Output: {output_path}")
    print(f"       Frames: {frame_count}")
    print(f"       FPS   : {fps:.2f}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert left/right image topics in a GVINS rosbag to videos."
    )

    parser.add_argument("--bag", required=True, help="Input rosbag path")

    parser.add_argument(
        "--left-topic",
        default="/cam0/image_raw",
        help="Left camera image topic",
    )

    parser.add_argument(
        "--right-topic",
        default="/cam1/image_raw",
        help="Right camera image topic",
    )

    parser.add_argument(
        "--output-dir",
        default="gvins_videos",
        help="Directory for output videos",
    )

    parser.add_argument(
        "--left-name",
        default="left.mp4",
        help="Output filename for left video",
    )

    parser.add_argument(
        "--right-name",
        default="right.mp4",
        help="Output filename for right video",
    )

    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Output fps. If not set, estimate from rosbag timestamps.",
    )

    parser.add_argument(
        "--codec",
        default="mp4v",
        help="OpenCV fourcc codec, e.g. mp4v, XVID, MJPG",
    )

    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Resize output width. Must be used with --height.",
    )

    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Resize output height. Must be used with --width.",
    )

    parser.add_argument(
        "--start-time",
        type=float,
        default=None,
        help="Start time in seconds relative to first image frame.",
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Duration in seconds to export.",
    )

    args = parser.parse_args()

    if (args.width is None) != (args.height is None):
        raise ValueError("Please provide both --width and --height, or neither.")

    resize = None
    if args.width is not None and args.height is not None:
        resize = (args.width, args.height)

    os.makedirs(args.output_dir, exist_ok=True)

    left_output = os.path.join(args.output_dir, args.left_name)
    right_output = os.path.join(args.output_dir, args.right_name)

    print("[INFO] Input bag:", args.bag)
    print("[INFO] Left topic :", args.left_topic)
    print("[INFO] Right topic:", args.right_topic)

    convert_topic_to_video(
        bag_path=args.bag,
        topic=args.left_topic,
        output_path=left_output,
        fps=args.fps,
        codec=args.codec,
        resize=resize,
        start_time=args.start_time,
        duration=args.duration,
    )

    convert_topic_to_video(
        bag_path=args.bag,
        topic=args.right_topic,
        output_path=right_output,
        fps=args.fps,
        codec=args.codec,
        resize=resize,
        start_time=args.start_time,
        duration=args.duration,
    )


if __name__ == "__main__":
    main()
