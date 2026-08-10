import numpy as np

blaze_pose_landmarks = [
        "nose", "inner left eye", "left eye", "outer left eye", "inner right eye", "right eye", "outer right eye",
        "left ear", "right ear", "mouth left", "mouth right", "left shoulder", "right shoulder", "left elbow",
        "right elbow", "left wrist", "right wrist", "left pinky", "right pinky", "left index", "right index",
        "left thumb", "right thumb", "left hip", "right hip", "left knee", "right knee", "left ankle", "right ankle",
        "left heel", "right heel", "left foot index", "right foot index"
]

BLAZE_HAND_LANDMARKS = [
    # Wrist / Root Origin (0)
    "WRIST",  # Index 0

    # Thumb (1 - 4)
    "THUMB_CMC",  # Index 1: Carpometacarpal joint
    "THUMB_MCP",  # Index 2: Metacarpophalangeal joint
    "THUMB_IP",   # Index 3: Interphalangeal joint
    "THUMB_TIP",  # Index 4: Tip of thumb

    # Index Finger (5 - 8)
    "INDEX_FINGER_MCP",  # Index 5: Knuckle
    "INDEX_FINGER_PIP",  # Index 6: Proximal joint
    "INDEX_FINGER_DIP",  # Index 7: Distal joint
    "INDEX_FINGER_TIP",  # Index 8: Tip of index finger

    # Middle Finger (9 - 12)
    "MIDDLE_FINGER_MCP", # Index 9: Knuckle
    "MIDDLE_FINGER_PIP", # Index 10: Proximal joint
    "MIDDLE_FINGER_DIP", # Index 11: Distal joint
    "MIDDLE_FINGER_TIP", # Index 12: Tip of middle finger

    # Ring Finger (13 - 16)
    "RING_FINGER_MCP",   # Index 13: Knuckle
    "RING_FINGER_PIP",   # Index 14: Proximal joint
    "RING_FINGER_DIP",   # Index 15: Distal joint
    "RING_FINGER_TIP",   # Index 16: Tip of ring finger

    # Pinky Finger (17 - 20)
    "PINKY_MCP",         # Index 17: Knuckle
    "PINKY_PIP",         # Index 18: Proximal joint
    "PINKY_DIP",         # Index 19: Distal joint
    "PINKY_TIP",         # Index 20: Tip of pinky finger
]

# The 5 primary MCP joints (knuckles) used with the WRIST (0) to calculate palm scale
KNUCKLE_INDICES = [1, 5, 9, 13, 17]
# Mapping finger chains to landmark indices for easy iteration
HAND_FINGER_CHAINS = {
    "thumb":  [1, 2, 3, 4],
    "index":  [5, 6, 7, 8],
    "middle": [9, 10, 11, 12],
    "ring":   [13, 14, 15, 16],
    "pinky":  [17, 18, 19, 20]
}


####################################################################################
#                   ELBOW/ARM OVERALL POSITION EVALUATION
###################################################################################
def eval_elbow_pos (
        user_frames: np.ndarray,
        ref_frames: np.ndarray,
        path: list[tuple[int, int]]
        ) -> str:
    # frames are of the shape (F, 75, 3)
    # body -> 13, 14 (l,r elbows)
    NOISE_THRESHOLD = 0
    DISTANCE_TOLERANCE = 0
    AXIS_TOLERANCE = 0
    delta_list = []

    for r_idx, u_idx in path:
        u_body = user_frames[u_idx][:33]
        r_body = ref_frames[r_idx][:33]
        ul_elbow_vec, ur_elbow_vec = u_body[13:15]
        rl_elbow_vec, rr_elbow_vec = r_body[13:15]

        delta_list.append(ul_elbow_vec - rl_elbow_vec)
        delta_list.append(ur_elbow_vec - rr_elbow_vec)

    # 1. Compute per-axis average and standard deviation
    avg_delta = np.mean(delta_list, axis=0)  # [avg_dx, avg_dy, avg_dz]
    std_delta = np.std(delta_list, axis=0)   # [std_dx, std_dy, std_dz]

    # 2. Check 3D Consistency across all axes
    # All axes must have low std dev (low jitter / steady trajectory)
    is_consistent = np.all(std_delta < NOISE_THRESHOLD)

    # 3. Check 3D Significance (Total spatial error magnitude)
    total_error_distance = np.linalg.norm(avg_delta)  # sqrt(dx^2 + dy^2 + dz^2)
    is_significant = total_error_distance > DISTANCE_TOLERANCE

    if is_consistent and is_significant:
        avg_dx, avg_dy, avg_dz = avg_delta
        directions = []

        # Evaluate X-Axis (Left / Right)
        if avg_dx > AXIS_TOLERANCE:
            directions.append("more to the left")
        elif avg_dx < -AXIS_TOLERANCE:
            directions.append("more to the right")

        # Evaluate Y-Axis (Up / Down)
        if avg_dy > AXIS_TOLERANCE:
            directions.append("lower")
        elif avg_dy < -AXIS_TOLERANCE:
            directions.append("higher")

        # Evaluate Z-Axis (Depth: Towards / Away from chest)
        if avg_dz > AXIS_TOLERANCE:
            directions.append("closer to your body")
        elif avg_dz < -AXIS_TOLERANCE:
            directions.append("further forward")

        # Construct combined natural human feedback
        feedback = ""
        if directions:
            feedback = f"Point your forearm {' and '.join(directions)} throughout the main sign movement."
        return feedback
    return "Pose is OK."

####################################################################################
#                   WRIST POSITION EVALUATION
###################################################################################
def eval_wrist_pos (
        user_frames: np.ndarray,
        ref_frames: np.ndarray,
        path: list[tuple[int, int]]
        ) -> str | None:
    # frames are of the shape (F, 75, 3)
    # 13, 14 (l,r elbows)
    # 15, 16 (l,r wrists)
    # TODO
    NOISE_THRESHOLD = 0
    DISTANCE_TOLERANCE = 0
    AXIS_TOLERANCE = 0
    delta_list = []

    for r_idx, u_idx in path:
        u_body = user_frames[u_idx][:33]
        r_body = ref_frames[r_idx][:33]

        ul_elbow_vec, ur_elbow_vec = u_body[13:15]
        rl_elbow_vec, rr_elbow_vec = r_body[13:15]
        ul_wrist_vec, ur_wrist_vec = u_body[15:17]
        rl_wrist_vec, rr_wrist_vec = r_body[15:17]
        normalized_ul_wrist_vec = ul_wrist_vec - ul_elbow_vec
        normalized_ur_wrist_vec = ur_wrist_vec - ur_elbow_vec
        normalized_rl_wrist_vec = rl_wrist_vec - rl_elbow_vec
        normalized_rr_wrist_vec = rr_wrist_vec - rr_elbow_vec

        delta_list.append(normalized_ul_wrist_vec - normalized_rl_wrist_vec)
        delta_list.append(normalized_ur_wrist_vec - normalized_rr_wrist_vec)

    # 1. Compute per-axis average and standard deviation
    avg_delta = np.mean(delta_list, axis=0)  # [avg_dx, avg_dy, avg_dz]
    std_delta = np.std(delta_list, axis=0)   # [std_dx, std_dy, std_dz]

    # 2. Check 3D Consistency across all axes
    # All axes must have low std dev (low jitter / steady trajectory)
    is_consistent = np.all(std_delta < NOISE_THRESHOLD)

    # 3. Check 3D Significance (Total spatial error magnitude)
    total_error_distance = np.linalg.norm(avg_delta)  # sqrt(dx^2 + dy^2 + dz^2)
    is_significant = total_error_distance > DISTANCE_TOLERANCE

    if is_consistent and is_significant:
        avg_dx, avg_dy, avg_dz = avg_delta
        directions = []

        # Evaluate X-Axis (Left / Right)
        if avg_dx > AXIS_TOLERANCE:
            directions.append("more to the left")
        elif avg_dx < -AXIS_TOLERANCE:
            directions.append("more to the right")

        # Evaluate Y-Axis (Up / Down)
        if avg_dy > AXIS_TOLERANCE:
            directions.append("lower")
        elif avg_dy < -AXIS_TOLERANCE:
            directions.append("higher")

        # Evaluate Z-Axis (Depth: Towards / Away from chest)
        if avg_dz > AXIS_TOLERANCE:
            directions.append("closer to your body")
        elif avg_dz < -AXIS_TOLERANCE:
            directions.append("further forward")

        # Construct combined natural human feedback
        feedback = ""
        if directions:
            feedback = f"Move your forearm {' and '.join(directions)} throughout the main sign movement."
        return feedback
    return "Forearm position is OK."

####################################################################################
#                   FINGER POSITION EVALUATION
###################################################################################
def __normalize_hand_bones (user_lhand: np.ndarray, ref_lhand: np.ndarray):
    u_hand = user_lhand.copy()
    r_hand = ref_lhand.copy()

    # subtract wrist from all the bones, including the wrist itself
    u_hand -= u_hand[0]
    r_hand -= r_hand[0]

    # calculate palm size and subtract it from all bones, apart from the wrist
    # palm size = middle finger knucke - wrist(euclidean distance)
    u_palm_size = np.linalg.norm(u_hand[KNUCKLE_INDICES[2]])
    r_palm_size = np.linalg.norm(r_hand[KNUCKLE_INDICES[2]])

    u_hand /= (u_palm_size if u_palm_size > 1e-6 else 1.0)
    r_hand /= (r_palm_size if r_palm_size > 1e-6 else 1.0)

    return u_hand, r_hand

def __calculate_extension_ratio (hand_bones):
    wrist = np.array([0, 0, 0])
    ratios = []
    for indices in  HAND_FINGER_CHAINS.values():
        tip_idx = indices[-1]
        tip_wrist_dist = np.linalg.norm(hand_bones[tip_idx] - wrist)
        total_finger_bone_len = 0.0
        for i in range (0, len(indices)-1):
            bone_vec = hand_bones[indices[i+1]] - hand_bones[indices[i]]
            total_finger_bone_len += np.linalg.norm(bone_vec)

        if total_finger_bone_len > 1e-6:
            ratios.append(tip_wrist_dist / total_finger_bone_len)
        else:
            ratios.append(0.0)

    return np.array([ratios])

# Structure for evaluating a single finger phase
def __eval_finger_curl_ratio(user_hand, ref_hand) -> np.ndarray:
    user_ext = __calculate_extension_ratio(user_hand)
    ref_ext  = __calculate_extension_ratio(ref_hand)
    ext_diff = user_ext - ref_ext
    return ext_diff

def __eval_finger_spread (user_hand, ref_hand) -> np.ndarray:
    user_finger_spread_angles, ref_finger_spread_angles = [], []
    finger_indices = list(HAND_FINGER_CHAINS.values())

    for i in range (0, len(finger_indices)-1):
        # knuckle to proximal joint for finger i
        u_bone1_vec = user_hand[finger_indices[i][1]] - user_hand[finger_indices[i][0]]
        r_bone1_vec = ref_hand[finger_indices[i][1]] - ref_hand[finger_indices[i][0]]

        # knuckle to proximal joint for finger i+1
        u_bone2_vec = user_hand[finger_indices[i+1][1]] - user_hand[finger_indices[i+1][0]]
        r_bone2_vec = ref_hand[finger_indices[i+1][1]] - ref_hand[finger_indices[i+1][0]]

        # u_bones interior angle
        u_dot_product = np.dot(u_bone1_vec, u_bone2_vec)
        u_norm_product = np.linalg.norm(u_bone1_vec) * np.linalg.norm(u_bone2_vec)
        user_finger_spread_angles.append(np.degrees(np.arccos(np.clip(u_dot_product/u_norm_product, -1.0, 1.0))))

        # r_bones interior angle
        r_dot_product = np.dot(r_bone1_vec, r_bone2_vec)
        r_norm_product = np.linalg.norm(r_bone1_vec) * np.linalg.norm(r_bone2_vec)
        ref_finger_spread_angles.append(np.degrees(np.arccos(np.clip(r_dot_product/r_norm_product, -1.0, 1.0))))

    angle_diffs = np.array([user_finger_spread_angles]) - np.array([ref_finger_spread_angles])
    return angle_diffs

def eval_finger_pos (
        u_frames: np.ndarray,
        r_frames: np.ndarray,
        path: list[tuple[int, int]],
        curl_tolerance: float = 0.2,
        spread_tolerance_deg: float = 12.0,
        noise_threshold: float = 8.0
        ) -> list[str]:
    # frames, (F, 75, 3)

    lhand_curl_history = []
    rhand_curl_history = []
    lhand_spread_history = []
    rhand_spread_history = []
    finger_names = list(HAND_FINGER_CHAINS.keys())
    spread_pairs = [("thumb", "index"), ("index", "middle"), ("middle", "ring"), ("ring", "pinky")]

    for r_idx, u_idx in path:
        u_lhand, u_rhand = u_frames[u_idx][33:53], u_frames[u_idx][54:]
        r_lhand, r_rhand = r_frames[r_idx][33:53], r_frames[r_idx][54:]

        u_lhand_norm, r_lhand_norm = __normalize_hand_bones(u_lhand, r_lhand)
        lhand_curl_history.append(__eval_finger_curl_ratio(u_lhand_norm, r_lhand_norm))
        lhand_spread_history.append(__eval_finger_spread(u_lhand_norm, r_lhand_norm))

        u_rhand_norm, r_rhand_norm = __normalize_hand_bones(u_rhand, r_rhand)
        rhand_curl_history.append(__eval_finger_curl_ratio(u_rhand_norm, r_rhand_norm))
        rhand_spread_history.append(__eval_finger_spread(u_rhand_norm, r_rhand_norm))

    feedback = []

    # 3. Perform Temporal Aggregation on the accumulated history arrays
    def process_history(history, names, is_spread=False, hand_label="right"):
        # if not history:
        #     return

        # Convert list of 1D arrays into 2D Matrix: Shape (N_frames, N_metrics)
        history_matrix = np.array(history)

        # Aggregate statistics down time axis
        avg_deltas = np.mean(history_matrix, axis=0) # Shape: (N_metrics,)
        std_deltas = np.std(history_matrix, axis=0)  # Shape: (N_metrics,)

        for i, (avg, std) in enumerate(zip(avg_deltas, std_deltas)):
            tol = spread_tolerance_deg if is_spread else curl_tolerance
            n_thresh = noise_threshold * 2.0 if is_spread else noise_threshold

            if std < n_thresh and abs(avg) > tol:
                if not is_spread:
                    # Curl Feedback
                    fname = names[i]
                    if avg < -tol:
                        feedback.append(f"Extend your {hand_label} {fname} finger more.")
                    else:
                        feedback.append(f"Curl your {hand_label} {fname} finger more.")
                else:
                    # Spread Feedback
                    f1, f2 = names[i]
                    if avg < -tol:
                        feedback.append(f"Spread your {hand_label} {f1} and {f2} fingers wider apart.")
                    else:
                        feedback.append(f"Keep your {hand_label} {f1} and {f2} fingers closer together.")

    # Generate feedback for both hands
    process_history(lhand_curl_history, finger_names, is_spread=False, hand_label="left")
    process_history(rhand_curl_history, finger_names, is_spread=False, hand_label="right")
    process_history(lhand_spread_history, spread_pairs, is_spread=True, hand_label="left")
    process_history(rhand_spread_history, spread_pairs, is_spread=True, hand_label="right")

    return feedback
