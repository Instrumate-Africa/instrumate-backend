import os
import json
import math
import argparse
import numpy as np
from pathlib import Path

def __least_cost_path(grid) -> list[tuple[int, int]]:
    rows, cols = len(grid), len(grid[0])
    path = [(0, 0)]
    r_idx, u_idx = 0, 0
    while r_idx + 1 < rows or u_idx + 1 < cols:
        if r_idx + 1 >= rows:
            u_idx += 1
        elif u_idx + 1 >= cols:
            r_idx += 1
        else:
            str8  = grid[r_idx+1][u_idx+1]
            down  = grid[r_idx+1][u_idx]
            right = grid[r_idx][u_idx+1]
            choice = min(str8, down, right)
            if choice == str8: r_idx, u_idx = r_idx+1, u_idx+1
            elif choice == down: r_idx += 1
            else: u_idx += 1
        path.append((r_idx, u_idx))
    return path

def np_dynamic_time_warp (norm_reference_frames: np.ndarray, norm_user_frames: np.ndarray) -> list[tuple[int, int]]:
    # frames are ndarrays of shape (#frames, 75, 3)
    grid = np.linalg.norm(norm_reference_frames[:, None] - norm_user_frames[None], axis=-1).sum(axis=-1)
    return __least_cost_path (grid)

def dynamic_time_warp (reference_frames: list[dict], user_frames: list[dict]) -> list[tuple[int, int]]:

    rows = len(reference_frames)
    cols = len(user_frames)
    grid: list[list[float]] = [[0.0 for _ in range(cols)] for _ in range(rows)]

    for r_idx, r_frame in enumerate(reference_frames):
        r_body, r_rhand, r_lhand = (r_frame.get('body', []), r_frame.get('right_hand', []), r_frame.get('left_hand', []))
        for u_idx, u_frame in enumerate(user_frames):
            u_body, u_rhand, u_lhand = (u_frame.get('body', []), u_frame.get('right_hand', []), u_frame.get('left_hand', []))

            hands_array = [u_lhand, r_lhand] if len(u_lhand) != 0 or len(r_lhand) != 0 else [u_rhand, r_rhand]

            cumulative_frame_landmark_euclidean_distance = 0
            for u_bone, r_bone in zip(u_body, r_body):
                ux, uy, uz = (u_bone['x'], u_bone['y'], u_bone['z'])
                rx, ry, rz = (r_bone['x'], r_bone['y'], r_bone['z'])
                ed = math.sqrt((ux-rx)**2 + (uy-ry)**2 + (uz-rz)**2)
                cumulative_frame_landmark_euclidean_distance += ed

            for u_bone, r_bone in zip(hands_array[0], hands_array[1]):
                ux, uy, uz = (u_bone['x'], u_bone['y'], u_bone['z'])
                rx, ry, rz = (r_bone['x'], r_bone['y'], r_bone['z'])
                ed = math.sqrt((ux-rx)**2 + (uy-ry)**2 + (uz-rz)**2)
                cumulative_frame_landmark_euclidean_distance += ed

            # grid[row-> refs][col -> user]
            grid[r_idx][u_idx] = round(cumulative_frame_landmark_euclidean_distance, 4)

    return __least_cost_path (grid)

def main ():

    parser = argparse.ArgumentParser(
            description="""
            Compare input frames to reference frames and produce a JSON file
            with input frames as close as possible to the reference frames.
            """
            )

    parser.add_argument("-i", "--input-file", required=True,
                        help="Path to JSON file to be compared to the reference frames.")
    parser.add_argument("-r", "--reference-file", required=True,
                        help="Path to JSON file to compare <input-file> to.")
    parser.add_argument("-o", "--output-dir", default="out",
                        help="Path to output directory. File will be the same as <input-file>")

    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        raise Exception(f"[ERROR] '{args.input_file}' is not a valid file!")

    if not os.path.isfile(args.reference_file):
        raise Exception(f"[ERROR] '{args.reference_file}' is not a valid file!")

    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir)

    input_file = open(args.input_file,'r')
    reference_file = open(args.reference_file,'r')

    input_data = json.loads (input_file.read())
    ref_data = json.loads (reference_file.read())

    aligned_UR_frames = dynamic_time_warp (ref_data['frames'], input_data['frames'])

    full_input_filename = Path(args.input_file)
    out_file = os.path.join(args.output_dir, full_input_filename.stem)
    with open(out_file, 'w') as out:
        out.write(str(aligned_UR_frames))

if __name__ == "__main__":
    main ()
