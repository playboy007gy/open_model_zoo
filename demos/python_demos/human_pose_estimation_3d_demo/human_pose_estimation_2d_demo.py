#!/usr/bin/env python
"""
 Copyright (c) 2019 Intel Corporation
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
      http://www.apache.org/licenses/LICENSE-2.0
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

from argparse import ArgumentParser, SUPPRESS
import json
import os

import cv2
import numpy as np

from modules.inference_engine import InferenceEngine
from modules.input_reader import InputReader
from modules.draw import Plotter3d, draw_poses
from modules.parse_poses import parse_poses

if __name__ == '__main__':
    parser = ArgumentParser(description='Lightweight 2D human pose estimation demo. '
                                        'Press esc to exit, "p" to (un)pause video or process next image.',
                            add_help=False)
    args = parser.add_argument_group('Options')
    args.add_argument('-h', '--help', action='help', default=SUPPRESS,
                      help='Show this help message and exit.')
    args.add_argument('-m', '--model',
                      help='Required. Path to an .xml file with a trained model.',
                      type=str, required=True)
    args.add_argument('-i', '--input',
                      help='Required. Path to input image, images, video file or camera id.',
                      nargs='+', default='')
    args.add_argument('-d', '--device',
                      help='Optional. Specify the target device to infer on: CPU, GPU, FPGA, HDDL or MYRIAD. '
                           'The demo will look for a suitable plugin for device specified '
                           '(by default, it is CPU).',
                      type=str, default='CPU')
    args.add_argument('--height_size', help='Optional. Network input layer height size.', type=int, default=256)
    args.add_argument('--extrinsics_path',
                      help='Optional. Path to file with camera extrinsics.',
                      type=str, default=None)
    args.add_argument('--fx', type=np.float32, default=-1, help='Optional. Camera focal length.')
    args.add_argument('--no_show', help='Optional. Do not display output.', action='store_true')
    args = parser.parse_args()

    if args.input == '':
        raise ValueError('Please, provide input data.')

    stride = 8
    inference_engine = InferenceEngine(args.model, args.device, stride)
    canvas_2d = np.zeros((720, 1280, 3), dtype=np.uint8)
    plotter = Plotter3d(canvas_2d.shape[:2])
    canvas_2d_window_name = 'Canvas 2D'
    if not args.no_show:
        cv2.namedWindow(canvas_2d_window_name)
        cv2.setMouseCallback(canvas_2d_window_name, Plotter3d.mouse_callback)

    frame_provider = InputReader(args.input)
    is_video = frame_provider.is_video
    base_height = args.height_size
    fx = args.fx

    delay = 1
    esc_code = 27
    p_code = 112
    space_code = 32
    mean_time = 0
    for frame in frame_provider:
        current_time = cv2.getTickCount()
        input_scale = base_height / frame.shape[0]
        scaled_img = cv2.resize(frame, dsize=None, fx=input_scale, fy=input_scale)
        if fx < 0:  # Focal length is unknown
            fx = np.float32(0.8 * frame.shape[1])

        inference_result = inference_engine.infer(scaled_img)

        poses_2d = parse_poses(inference_result, input_scale, stride, fx, is_video)

        draw_poses(frame, poses_2d)
        current_time = (cv2.getTickCount() - current_time) / cv2.getTickFrequency()
        if mean_time == 0:
            mean_time = current_time
        else:
            mean_time = mean_time * 0.95 + current_time * 0.05
        cv2.putText(frame, 'FPS: {}'.format(int(1 / mean_time * 10) / 10),
                    (40, 80), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255))
        if args.no_show:
            continue
        cv2.imshow('2D Human Pose Estimation', frame)

        key = cv2.waitKey(delay)
        if key == esc_code:
            break
        if key == p_code:
            if delay == 1:
                delay = 0
            else:
                delay = 1
        if delay == 0 or not is_video:  
            key = 0
            while (key != p_code
                   and key != esc_code
                   and key != space_code):

                key = cv2.waitKey(33)
            if key == esc_code:
                break
            else:
                delay = 1
