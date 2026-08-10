# pyright: reportOptionalSubscript=false
import os
import json
import math
import argparse
import numpy as np
from pathlib import Path

def np_normalize (frames: np.ndarray) -> list:
    normalized_frames = []
    hip_centers = []
    shoulder_widths = []

    # each frame is a stack of all 75 landmarks, 33 for the body, and 21 for each hand
    for frame in frames:
        body = frame[:33]        # 0-32
        left_hand = frame[33:54] # 33 - 53
        right_hand = frame[54:]  # 54 - 74

        # average of left hip(23) and right hip(24)
        hip_center = np.round((body[23] + body[24])/2, 4)
        #Euclidean distance between left shoulder and right shoulder
        shoulder_width = np.linalg.norm(body[11]-body[12])

        normalized_body = np.round((body - hip_center) / shoulder_width, 4)

        normalized_lh = left_hand.copy()
        mask = np.any(left_hand != 0, axis=1)
        normalized_lh[mask] = np.round(
            (left_hand[mask] - hip_center) / shoulder_width,
            4
        )
        normalized_rh = right_hand.copy()
        mask = np.any(right_hand != 0, axis=1)
        normalized_rh[mask] = np.round(
            (right_hand[mask] - hip_center) / shoulder_width,
            4
        )
        normalized_frame = np.vstack([
            normalized_body,
            normalized_lh,
            normalized_rh
        ])
        hip_centers.append(hip_center)
        shoulder_widths.append(shoulder_width)
        normalized_frames.append(normalized_frame)

    output = [hip_centers, shoulder_widths, np.array([normalized_frames])]
    return output


def json_normalize (frames: list[dict]) -> list[dict]:

    normalized_frames: list[dict] = []

    for frame in frames:
        body = frame.get('body', [])
        left_hand = frame.get('left_hand', [])
        right_hand = frame.get('right_hand', [])
        normalized_frame = {}
        normalized_body = []
        normalized_hand_bones = []

        normalized_frame["frame"] = frame.get("frame")
        normalized_frame["timestamp_ms"] = frame.get("timestamp_ms")

        lh = body[23] # left hip
        rh = body[24] # right hip
        hip_center = {
                "x": round((lh["x"] + rh["x"])/2, 4),
                "y": round((lh["y"] + rh["y"])/2, 4),
                "z": round((lh["z"] + rh["z"])/2, 4)
                }
        normalized_frame["hip_center"] = hip_center

        ls = body[11] # left shoulder
        rs = body[12] # right shoulder
        shoulder_width = math.sqrt((ls['x'] - rs['x'])**2 + (ls['y'] - rs['y'])**2 + (ls['z'] - rs['z'])**2)
        normalized_frame["shoulder_width"] = round(shoulder_width, 4)

        for bone in body:
            normalized_bone = {
                    "x": round((bone['x'] - hip_center['x'])/shoulder_width, 4),
                    "y": round((bone['y'] - hip_center['y'])/shoulder_width, 4),
                    "z": round((bone['z'] - hip_center['z'])/shoulder_width, 4),
                    "visibility": bone['visibility']
            }
            normalized_body.append(normalized_bone)

        hand_bones = right_hand if len(left_hand) == 0 else left_hand
        hand_key, empty_hand_key  = ("right_hand", "left_hand") if len(left_hand) == 0 else  ("right_hand", "left_hand")
        for bone in hand_bones:
            normalized_bone = {
                    "x": round((bone['x'] - hip_center['x'])/shoulder_width, 4),
                    "y": round((bone['y'] - hip_center['y'])/shoulder_width, 4),
                    "z": round((bone['z'] - hip_center['z'])/shoulder_width, 4)
            }
            normalized_hand_bones.append(normalized_bone)

        normalized_frame["body"] = normalized_body
        normalized_frame[hand_key] = normalized_hand_bones
        normalized_frame[empty_hand_key] = []

        normalized_frames.append(normalized_frame)

    return normalized_frames

def main ():

    parser = argparse.ArgumentParser(description="Normalizing JSON animation coords whose landmarks are assumed to be in a BlazePose format.")

    parser.add_argument("-i", "--input", required=True,
                        help="Path to a video file or a directory of JSON files containing coords.")
    parser.add_argument("-o", "--output", default="out", help="Path to output<dir/file(if input is file)>")

    args = parser.parse_args()

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
        else:
            _ = open(args.output, "x")

    full_input_path: str = ''
    full_output_path: str = ''
    if input_is_dir:
        json_files = [f for f in os.listdir(args.input) if f.endswith('.json')]
        for file in json_files:
            json_filename: str = os.path.splitext(os.path.basename(file))[0]
            json_filename += "_normalized.json"
            full_input_path = os.path.join(args.input, file)
            full_output_path = os.path.join(args.output if output_is_dir else '', json_filename)
            in_file = open(full_input_path, "r")
            data = json.loads(in_file.read())
            normal_coords = json_normalize(data.get('frames'))
            out_json = {}
            out_json['fps'] = data.get('fps')
            out_json['total_frames'] = data.get('total_frames')
            out_json['frames'] = normal_coords
            out_file = open(full_output_path, 'w')
            out_file.write(json.dumps(out_json))
            out_file.close()
    else:
        full_in_filename = Path(args.input)
        json_filename = full_in_filename.stem + "_normalized.json"
        full_output_path = os.path.join(args.output if output_is_dir else '', json_filename)
        in_file = open(json_filename, "r")
        data = json.loads(in_file.read())
        normal_coords = json_normalize(data.get('frames'))
        out_json = {}
        out_json['fps'] = data.get('fps')
        out_json['total_frames'] = data.get('total_frames')
        out_json['frames'] = normal_coords
        out_file = open(full_output_path, 'w')
        out_file.write(json.dumps(out_json))
        out_file.close()

if __name__ == "__main__":
    main ()
