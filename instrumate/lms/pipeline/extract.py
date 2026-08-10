"""
Module for extracting 3D motion landmarks from videos using MediaPipe.
"""

import os
import cv2
import json
import argparse
import numpy as np
import urllib.request
import mediapipe as mp
from pathlib import Path

download_dir = '.'

def download_models () -> tuple[str, str]:
    """
    Downloads the necessary MediaPipe task models if they don't exist.

    Returns:
        tuple[str, str]: Paths to the pose and hand landmarker models.
    """
    models = {
        'pose': {
            'path': f'{download_dir}/pose_landmarker.task',
            'url': 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task'
        },
        'hand': {
            'path': f'{download_dir}/hand_landmarker.task',
            'url': 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task'
        }
    }
    for name, model in models.items():
        if not os.path.exists(model['path']):
            print(f"[INFO] Downloading {name} model...")
            urllib.request.urlretrieve(model['url'], model['path'])
            print(f"[OK] `{name}` model downloaded.")
    return models['pose']['path'], models['hand']['path']


def extract_sign_poses(video_path: str, output_as_numpy_array=False, target_fps: float = 30.0) -> dict | np.ndarray:
    """
    Extracts body and hand landmarks from a video and saves them to a JSON file.

    Args:
        video_path   (str):    Path to the source video file.
        target_fps   (float) : fps to extract coords at
    """

    pose_model_path, hand_model_path = download_models()

    # Pose setup
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    BaseOptions = mp.tasks.BaseOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    pose_options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=pose_model_path),
        running_mode=VisionRunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )

    hand_options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=hand_model_path),
        running_mode=VisionRunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"Error: Cannot open video {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = fps / target_fps if fps > target_fps else 1.0
    frame_accum = 0.0
    frame_count = 0
    poses = []

    with PoseLandmarker.create_from_options(pose_options) as pose_landmarker, \
         HandLandmarker.create_from_options(hand_options) as hand_landmarker:

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            frame_accum += 1.0
            if frame_accum < frame_interval:
                continue          # skip this native frame — keeps output near target_fps
            frame_accum -= frame_interval
            print(f"Processing frame {frame_count}/{total_frames}", end='\r')

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = int((frame_count / fps) * 1000)

            pose_result = pose_landmarker.detect_for_video(mp_image, timestamp_ms)
            hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)

            frame_data = {
                'frame': frame_count,
                'timestamp_ms': timestamp_ms,
                'body': [],
                'left_hand': [],
                'right_hand': []
            }

            # Body
            if pose_result.pose_landmarks:
                frame_data['body'] = [
                    {
                        'x': round(l.x, 4),
                        'y': round(l.y, 4),
                        'z': round(l.z, 4),
                        'visibility': round(l.visibility, 4)
                    }
                    for l in pose_result.pose_landmarks[0]
                ]

            # Hands
            if hand_result.hand_landmarks:
                assigned = set()
                for i, hand_landmarks in enumerate(hand_result.hand_landmarks):
                    handedness = hand_result.handedness[i][0].category_name
                    landmarks = [
                        {
                            'x': round(l.x, 4),
                            'y': round(l.y, 4),
                            'z': round(l.z, 4)
                        }
                        for l in hand_landmarks
                    ]
                    side = 'left_hand' if handedness == 'Left' else 'right_hand'
                    if side in assigned:
                        print(f"[WARN] Frame {frame_count}: both hands classified as {handedness}, second one dropped")
                    else:
                        frame_data[side] = landmarks
                        assigned.add(side)

            poses.append(frame_data)

    cap.release()

    if output_as_numpy_array:
        body = np.array([
            [
                [c["x"], c["y"], c["z"], c["visibility"]]
                for c in frame["body"]
            ]
            for frame in poses
            ])

        left = np.array([
            (
                [[c["x"], c["y"], c["z"]] for c in frame["left_hand"]]
                if len(frame["left_hand"]) != 0
                else np.zeros(shape=(21, 3))
            )
            for frame in poses
        ])

        right = np.array([
            (
                [[c["x"], c["y"], c["z"]] for c in frame["right_hand"]]
                if len(frame["right_hand"]) != 0
                else np.zeros(shape=(21, 3))
            )
            for frame in poses
        ])
        frames = np.array([
            np.vstack([
                b[:, :3],
                l,
                r
                ])
            for b, l, r in zip(body, left, right)
        ])
        return frames
    else:
        output = {
            'fps': fps,
            'total_frames': frame_count,
            'frames': poses
        }
        return output

def main ():

    global download_dir

    parser = argparse.ArgumentParser(description="Converting from Pose Video to JSON Coords")

    parser.add_argument("-i", "--input", required=True, help="Path to a video file or a directory of videos")
    parser.add_argument("-o", "--output", default="out", help="Path to output")
    parser.add_argument("-t", "--taskfile-dir", default="models",
                        help="Directory where landmarker task files will be downloaded/reside. "
                        )

    args = parser.parse_args()

    # Determine if we are looking at one file or a directory
    input_is_dir = False
    if os.path.isdir(args.input):
        input_is_dir=True
    elif os.path.isfile(args.input):
        pass
    else:
        raise Exception(f"[ERROR] '{args.input}' is not a valid file or directory")

    output_is_dir = False
    if os.path.isdir(args.output):
        output_is_dir=True
    elif os.path.isfile(args.output):
        pass
    else:
        if input_is_dir:
            if args.output_dir == "out":
                os.makedirs(args.output)
            else:
                raise Exception(f"[ERROR] '{args.output}' has to be a directory since {args.input} is a directory.")
        _ = open(args.output, "x")

    if not os.path.isdir(args.taskfile_dir):
        os.makedirs(args.taskfile_dir)
        download_models()

    download_dir = args.taskfile_dir

    if input_is_dir:
        vid_files = [f for f in os.listdir(args.input) if f.endswith(('.mp4', '.mov', '.avi', '.mkv'))]
        for vid in vid_files:
            sign_filename: str = os.path.splitext(os.path.basename(vid))[0]

            full_input_path: str  = os.path.join(args.input, vid)
            full_output_path: str = os.path.join(args.output if output_is_dir else '', sign_filename)
            output = extract_sign_poses(full_input_path)
            with open(full_output_path, 'w') as f:
                json.dump(output, f)
            print(f"[INFO] Done! Saved to {full_output_path}")
            print(f"[INFO] File size: {round(os.path.getsize(full_output_path) / 1024, 1)} KB")
    else:
        full_input_filepath = Path(args.input)
        full_output_path = os.path.join(args.output if output_is_dir else '', full_input_filepath.stem)
        output = extract_sign_poses(args.input)
        with open(full_output_path, 'w') as f:
            json.dump(output, f)
        print(f"[INFO] Done! Saved to {full_output_path}")
        print(f"[INFO] File size: {round(os.path.getsize(full_output_path) / 1024, 1)} KB")

if __name__ == "__main__":
    main()
