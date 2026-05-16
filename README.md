# my_ros_toolkit

Utility scripts for ROS bag processing and video inspection.

This repository provides small command-line tools for common GVINS dataset workflows, including extracting camera videos from bags, trimming bags by time, applying image degradation, and generating fast-forward preview videos.

## Environment

Source the catkin workspace before running the tools:

```bash
cd ~/Development/catkin_ws
source devel/setup.bash
```

All scripts are intended to be executed with `rosrun`:

```bash
rosrun my_ros_toolkit <script_name>.py [arguments]
```

Example dataset and output paths used in this document:

```text
~/Development/datasets/\[HKUST\]GVINS_Dataset/
~/Development/gvins_experiment/output_temp/
```

---

## 1. Extract Camera Images from a Bag

Script:

```text
bag_images_to_videos.py
```

Usage:

```bash
rosrun my_ros_toolkit bag_images_to_videos.py \
  --bag ~/Development/datasets/\[HKUST\]GVINS_Dataset/sports_field.bag \
  --output-dir ~/Development/gvins_experiment/output_temp/sports_field_video
```

Purpose:

Convert camera image topics in a ROS bag into video files for quick dataset inspection.

---

## 2. Cut a Bag by Time

Script:

```text
cut_bag_by_time.py
```

Usage:

```bash
rosrun my_ros_toolkit cut_bag_by_time.py \
  --input ~/Development/datasets/\[HKUST\]GVINS_Dataset/sports_field.bag \
  --output ~/Development/gvins_experiment/output_temp/sports_field_cut.bag \
  --start 10 \
  --end 40
```

Purpose:

Create a new ROS bag containing only the selected time interval.

In this example, the output bag contains data from 10 seconds to 40 seconds after the beginning of the input bag.

---

## 3. Apply Image Degradation to a GVINS Bag

Script:

```text
degrade_gvins_bag.py
```

Usage:

```bash
rosrun my_ros_toolkit degrade_gvins_bag.py \
  --input ~/Development/datasets/\[HKUST\]GVINS_Dataset/urban_driving.bag \
  --output ~/Development/gvins_experiment/output_temp/urban_driving_motion_blur.bag \
  --blur-type motion \
  --blur-kernel 15 \
  --motion-angle 0 \
  --noise-std 5.0 \
  --export-images ~/Development/gvins_experiment/output_temp/debug_motion \
  --max-images-per-topic 20
```

Purpose:

Generate a degraded version of a GVINS ROS bag by applying image degradation to camera topics.

Common options:

```text
--blur-type              Type of blur to apply, for example motion
--blur-kernel            Blur kernel size
--motion-angle           Motion blur direction in degrees
--noise-std              Standard deviation of added image noise
--export-images          Directory for exported debug images
--max-images-per-topic   Maximum number of debug images exported per topic
```

Note:

`--max-images-per-topic` only limits the number of exported debug images. It does not limit how many images are processed into the output bag.

---

## 4. Generate a Fast-Forward Video

Script:

```text
fast_forward_video.py
```

Usage:

```bash
rosrun my_ros_toolkit fast_forward_video.py \
  --input ~/Development/gvins_experiment/output_temp/sports_field_video/left.mp4 \
  --output ~/Development/gvins_experiment/output_temp/sports_field_video/left_8x.mp4 \
  --speed 8 \
  --watermark
```

Purpose:

Create a fast-forward version of an input video for rapid visual inspection.

In this example, the output video is generated at 8x speed.

Note:

The output path should include a valid video extension, such as `.mp4`.

---

## Help

Print the available arguments for each script:

```bash
rosrun my_ros_toolkit bag_images_to_videos.py --help
rosrun my_ros_toolkit cut_bag_by_time.py --help
rosrun my_ros_toolkit degrade_gvins_bag.py --help
rosrun my_ros_toolkit fast_forward_video.py --help
```

---

## Common Checks

Inspect a ROS bag:

```bash
rosbag info ~/Development/datasets/\[HKUST\]GVINS_Dataset/sports_field.bag
```

List topics in a ROS bag:

```bash
rostopic list -b ~/Development/datasets/\[HKUST\]GVINS_Dataset/sports_field.bag
```

Check output files:

```bash
ls -lh ~/Development/gvins_experiment/output_temp/
```

---

## Fish Shell Path Completion for `rosrun`

When using fish shell, ROS completion may prevent normal file path completion after `rosrun <package> <script>`.

Add the following rule to `~/.config/fish/config.fish` after sourcing the ROS and catkin setup files:

`````fish
# ROS fish completion makes rosrun completion exclusive.
# Re-enable normal file path completion after: rosrun <pkg> <script> ...
complete -c rosrun \
  -n 'test (count (commandline -opc)) -ge 4' \
  -F
``` my_ros_toolkit
```` my_ros_toolkit
`````
