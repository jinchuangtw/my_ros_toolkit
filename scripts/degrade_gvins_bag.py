#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Degrade stereo images in HKUST GVINS rosbag.

Official GVINS-Dataset image topics:
  /cam0/image_raw : right camera
  /cam1/image_raw : left camera

This script:
  1. Reads an input rosbag.
  2. Modifies only stereo image topics.
  3. Preserves all other messages unchanged.
  4. Writes a new rosbag for GVINS testing.
  5. Optionally exports degraded images to folders for inspection.

Tested design target:
  ROS Noetic + Python3 + cv_bridge + OpenCV
"""

import os
import argparse
import numpy as np
import cv2
import rosbag
from cv_bridge import CvBridge
from sensor_msgs.msg import Image


DEFAULT_IMAGE_TOPICS = [
    "/cam0/image_raw",  # right camera, according to HKUST official dataset repo
    "/cam1/image_raw",  # left camera, according to HKUST official dataset repo
]


def ensure_odd(k: int) -> int:
    """Gaussian kernel size must be positive odd."""
    if k <= 1:
        return 1
    return k if k % 2 == 1 else k + 1


def apply_gaussian_blur(img: np.ndarray, kernel_size: int, sigma: float) -> np.ndarray:
    kernel_size = ensure_odd(kernel_size)
    if kernel_size <= 1:
        return img
    return cv2.GaussianBlur(img, (kernel_size, kernel_size), sigmaX=sigma, sigmaY=sigma)


def apply_motion_blur(
    img: np.ndarray, kernel_size: int, angle_deg: float
) -> np.ndarray:
    """
    Simple linear motion blur.
    Useful for simulating fast ego-motion / exposure-like smearing.
    """
    kernel_size = ensure_odd(kernel_size)
    if kernel_size <= 1:
        return img

    kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
    center = kernel_size // 2
    kernel[center, :] = 1.0

    rot_mat = cv2.getRotationMatrix2D((center, center), angle_deg, 1.0)
    kernel = cv2.warpAffine(kernel, rot_mat, (kernel_size, kernel_size))
    kernel = kernel / np.sum(kernel)

    return cv2.filter2D(img, -1, kernel)


def add_gaussian_noise(img: np.ndarray, noise_std: float) -> np.ndarray:
    """
    Add zero-mean Gaussian noise.
    noise_std is in pixel intensity scale, e.g. 5, 10, 20.
    """
    if noise_std <= 0:
        return img

    img_float = img.astype(np.float32)
    noise = np.random.normal(0.0, noise_std, img.shape).astype(np.float32)
    noisy = img_float + noise
    return np.clip(noisy, 0, 255).astype(img.dtype)


def add_brightness_drop(img: np.ndarray, brightness_scale: float) -> np.ndarray:
    """
    brightness_scale < 1.0 simulates darker images.
    Example: 0.6 means 60% brightness.
    """
    if brightness_scale == 1.0:
        return img

    img_float = img.astype(np.float32) * brightness_scale
    return np.clip(img_float, 0, 255).astype(img.dtype)


def add_jpeg_compression(img: np.ndarray, quality: int) -> np.ndarray:
    """
    Simulate compression artifacts.
    quality: 1-100. Lower means stronger artifacts.
    """
    if quality >= 100:
        return img

    quality = int(np.clip(quality, 1, 100))

    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]

    if img.ndim == 2:
        ok, enc = cv2.imencode(".jpg", img, encode_param)
        if not ok:
            return img
        return cv2.imdecode(enc, cv2.IMREAD_GRAYSCALE)

    ok, enc = cv2.imencode(".jpg", img, encode_param)
    if not ok:
        return img
    return cv2.imdecode(enc, cv2.IMREAD_UNCHANGED)


def degrade_image(img: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    """
    Degradation order:
      brightness drop -> blur -> noise -> JPEG artifacts

    This order is intentional:
      - challenging lighting first
      - optical/motion blur next
      - sensor noise after blur
      - optional codec artifact last
    """
    out = img.copy()

    out = add_brightness_drop(out, args.brightness_scale)

    if args.blur_type == "gaussian":
        out = apply_gaussian_blur(out, args.blur_kernel, args.gaussian_sigma)
    elif args.blur_type == "motion":
        out = apply_motion_blur(out, args.blur_kernel, args.motion_angle)
    elif args.blur_type == "both":
        out = apply_gaussian_blur(out, args.blur_kernel, args.gaussian_sigma)
        out = apply_motion_blur(out, args.motion_kernel, args.motion_angle)
    elif args.blur_type == "none":
        pass
    else:
        raise ValueError(f"Unknown blur_type: {args.blur_type}")

    out = add_gaussian_noise(out, args.noise_std)
    out = add_jpeg_compression(out, args.jpeg_quality)

    return out


def export_debug_image(export_root: str, topic: str, stamp_ns: int, img: np.ndarray):
    """
    Save degraded images for visual inspection.
    Folder names are made filesystem-safe from topic names.
    """
    topic_folder = topic.strip("/").replace("/", "_")
    out_dir = os.path.join(export_root, topic_folder)
    os.makedirs(out_dir, exist_ok=True)

    filename = f"{stamp_ns}.png"
    path = os.path.join(out_dir, filename)
    cv2.imwrite(path, img)


def main():
    parser = argparse.ArgumentParser(
        description="Degrade HKUST GVINS stereo images and write a new rosbag."
    )

    parser.add_argument("--input", "-i", required=True, help="Input rosbag path")
    parser.add_argument("--output", "-o", required=True, help="Output rosbag path")

    parser.add_argument(
        "--image-topics",
        nargs="+",
        default=DEFAULT_IMAGE_TOPICS,
        help="Image topics to degrade. Default: /cam0/image_raw /cam1/image_raw",
    )

    parser.add_argument(
        "--blur-type",
        choices=["none", "gaussian", "motion", "both"],
        default="gaussian",
        help="Blur type",
    )
    parser.add_argument(
        "--blur-kernel",
        type=int,
        default=7,
        help="Gaussian blur kernel size. Will be forced to odd.",
    )
    parser.add_argument(
        "--gaussian-sigma",
        type=float,
        default=2.0,
        help="Gaussian blur sigma",
    )
    parser.add_argument(
        "--motion-kernel",
        type=int,
        default=9,
        help="Motion blur kernel size. Used when --blur-type both.",
    )
    parser.add_argument(
        "--motion-angle",
        type=float,
        default=0.0,
        help="Motion blur angle in degrees",
    )
    parser.add_argument(
        "--noise-std",
        type=float,
        default=0.0,
        help="Gaussian noise std in pixel intensity scale",
    )
    parser.add_argument(
        "--brightness-scale",
        type=float,
        default=1.0,
        help="Brightness scale. Example: 0.7 makes images darker.",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=100,
        help="JPEG quality for artifact simulation. 100 disables it.",
    )

    parser.add_argument(
        "--export-images",
        default="",
        help="Optional folder to export degraded images for inspection.",
    )
    parser.add_argument(
        "--max-images-per-topic",
        type=int,
        default=0,
        help="Optional limit for exporting debug images. 0 means no limit.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for reproducible Gaussian noise.",
    )

    args = parser.parse_args()

    np.random.seed(args.seed)
    bridge = CvBridge()

    image_topics = set(args.image_topics)
    exported_count = {topic: 0 for topic in image_topics}
    processed_count = {topic: 0 for topic in image_topics}

    print("[INFO] Input bag :", args.input)
    print("[INFO] Output bag:", args.output)
    print("[INFO] Degrading image topics:", sorted(image_topics))
    print("[INFO] Blur type:", args.blur_type)

    with rosbag.Bag(args.input, "r") as inbag, rosbag.Bag(args.output, "w") as outbag:
        for topic, msg, t in inbag.read_messages():
            if topic in image_topics:
                try:
                    cv_img = bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
                    degraded = degrade_image(cv_img, args)

                    new_msg = bridge.cv2_to_imgmsg(degraded, encoding=msg.encoding)
                    new_msg.header = msg.header

                    # Preserve original image metadata as much as possible.
                    # cv_bridge sets height, width, encoding, step, data.
                    # is_bigendian is not always preserved by cv_bridge.
                    new_msg.is_bigendian = msg.is_bigendian

                    outbag.write(topic, new_msg, t)
                    processed_count[topic] += 1

                    if args.export_images:
                        can_export = (
                            args.max_images_per_topic <= 0
                            or exported_count[topic] < args.max_images_per_topic
                        )
                        if can_export:
                            stamp_ns = msg.header.stamp.to_nsec()
                            export_debug_image(
                                args.export_images, topic, stamp_ns, degraded
                            )
                            exported_count[topic] += 1

                except Exception as e:
                    print(f"[WARN] Failed to process image on {topic} at {t}: {e}")
                    print("[WARN] Writing original message instead.")
                    outbag.write(topic, msg, t)
            else:
                # Preserve IMU, GNSS raw measurements, trigger, ephemeris, etc.
                outbag.write(topic, msg, t)

    print("[DONE] Processed image counts:")
    for topic in sorted(image_topics):
        print(f"  {topic}: {processed_count[topic]} images")

    if args.export_images:
        print("[DONE] Exported debug images:")
        for topic in sorted(image_topics):
            print(f"  {topic}: {exported_count[topic]} images")


if __name__ == "__main__":
    main()
