cmake_minimum_required(VERSION 3.0.2)
project(my_ros_toolkit)

find_package(catkin REQUIRED COMPONENTS rospy)

catkin_package()

catkin_install_python(PROGRAMS scripts/cut_bag_by_time.py DESTINATION
                      ${CATKIN_PACKAGE_BIN_DESTINATION})

catkin_install_python(PROGRAMS scripts/bag_images_to_videos.py DESTINATION
                      ${CATKIN_PACKAGE_BIN_DESTINATION})
catkin_install_python(PROGRAMS scripts/degrade_gvins_bag.py DESTINATION
                      ${CATKIN_PACKAGE_BIN_DESTINATION})
catkin_install_python(PROGRAMS scripts/fast_forward_video.py DESTINATION
                      ${CATKIN_PACKAGE_BIN_DESTINATION})
