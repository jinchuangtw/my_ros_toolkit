import argparse
import os
import sys
import rosbag
import rospy


def parse_args():
    parser = argparse.ArgumentParser(
        description="Cut a rosbag by relative time or absolute ROS time."
    )

    parser.add_argument("--input", required=True, help="Input rosbag path.")

    parser.add_argument("--output", required=True, help="Output rosbag path.")

    parser.add_argument(
        "--start",
        type=float,
        required=True,
        help=(
            "Start time. By default this is relative to the beginning of the bag, "
            "in seconds. Use --absolute if this is an absolute ROS timestamp."
        ),
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--end",
        type=float,
        help=(
            "End time. By default this is relative to the beginning of the bag, "
            "in seconds. Use --absolute if this is an absolute ROS timestamp."
        ),
    )

    group.add_argument("--duration", type=float, help="Duration in seconds.")

    parser.add_argument(
        "--absolute",
        action="store_true",
        help="Treat --start and --end as absolute ROS timestamps.",
    )

    parser.add_argument(
        "--topics",
        nargs="*",
        default=None,
        help=(
            "Optional topic whitelist. If omitted, all topics are copied. "
            "Example: --topics /cam0/image_raw /imu0"
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output bag if it already exists.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    input_bag = os.path.expanduser(args.input)
    output_bag = os.path.expanduser(args.output)

    if not os.path.exists(input_bag):
        print("[ERROR] Input bag does not exist: {}".format(input_bag))
        sys.exit(1)

    if os.path.exists(output_bag) and not args.force:
        print("[ERROR] Output bag already exists: {}".format(output_bag))
        print("        Use --force to overwrite it.")
        sys.exit(1)

    output_dir = os.path.dirname(os.path.abspath(output_bag))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with rosbag.Bag(input_bag, "r") as inbag:
        bag_start = inbag.get_start_time()
        bag_end = inbag.get_end_time()
        bag_duration = bag_end - bag_start

        if args.absolute:
            start_time = args.start

            if args.duration is not None:
                end_time = start_time + args.duration
            else:
                end_time = args.end
        else:
            start_time = bag_start + args.start

            if args.duration is not None:
                end_time = start_time + args.duration
            else:
                end_time = bag_start + args.end

        if start_time < bag_start:
            print("[WARN] Requested start time is before bag start.")
            print("       Clamping to bag start.")
            start_time = bag_start

        if end_time > bag_end:
            print("[WARN] Requested end time is after bag end.")
            print("       Clamping to bag end.")
            end_time = bag_end

        if end_time <= start_time:
            print("[ERROR] Invalid time range.")
            print("        bag start     : {:.9f}".format(bag_start))
            print("        bag end       : {:.9f}".format(bag_end))
            print("        request start : {:.9f}".format(start_time))
            print("        request end   : {:.9f}".format(end_time))
            sys.exit(1)

        print("[INFO] Input bag    : {}".format(input_bag))
        print("[INFO] Output bag   : {}".format(output_bag))
        print("[INFO] Bag start    : {:.9f}".format(bag_start))
        print("[INFO] Bag end      : {:.9f}".format(bag_end))
        print("[INFO] Bag duration : {:.3f} sec".format(bag_duration))
        print("[INFO] Cut start    : {:.9f}".format(start_time))
        print("[INFO] Cut end      : {:.9f}".format(end_time))
        print("[INFO] Cut duration : {:.3f} sec".format(end_time - start_time))

        if args.topics is None:
            print("[INFO] Topics        : all")
        else:
            print("[INFO] Topics        :")
            for topic in args.topics:
                print("                    {}".format(topic))

        start_ros_time = rospy.Time.from_sec(start_time)
        end_ros_time = rospy.Time.from_sec(end_time)

        msg_count = 0

        with rosbag.Bag(output_bag, "w") as outbag:
            for topic, msg, t in inbag.read_messages(
                topics=args.topics, start_time=start_ros_time, end_time=end_ros_time
            ):
                outbag.write(topic, msg, t)
                msg_count += 1

        print("[INFO] Done.")
        print("[INFO] Written messages: {}".format(msg_count))

        if msg_count == 0:
            print("[WARN] Output bag contains zero messages.")
            print("       Please check the time range and topic names.")


if __name__ == "__main__":
    main()
