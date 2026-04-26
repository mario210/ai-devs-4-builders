import json
import re
import os
from dotenv import load_dotenv
from loguru import logger

from ai.task import BaseTask
from ai.memory import SharedMemory
from ai.agent import AGENTS_API_KEY

from task.task24_goingthere.agents import (
    RocketControlAgent,
    TrapScannerAgent,
    RadioHintAgent,
)

# Load environment variables
load_dotenv()

BASE_URL = os.environ.get("HUB_API_BASE_URL")


# -------------------------------------------------
# 🔧 JSON SAFE PARSER
# -------------------------------------------------


def safe_json(text: str):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            return None
    return None


# -------------------------------------------------
# 💣 TRAP PARSER (LLM + PROGRAMMATIC)
# -------------------------------------------------


def call_trap_parser_llm(agent_model, text: str):
    """Uses an LLM to parse a messy string for trap details."""
    prompt = f"""
    You are an expert data extraction tool. Your task is to find the frequency and detection code from the following text, which might be a broken JSON or unstructured data.

    - The frequency key might be 'frequency', 'freq', 'FreqUENcY', 'frePUeNcy', etc.
    - The detection code key might be 'detectioncode', 'code', 'deTECtiOnCODE', 'BETeCTi0NC0be', etc., and it might be nested inside a 'data' or 'daTa' or 'baTA' object or similar.

    Extract the values and return them in a strict JSON format:
    {{
      "frequency": <number>,
      "code": "<string>"
    }}

    If you cannot find the values, return null.

    INPUT TEXT:
    ---
    {text}
    ---

    OUTPUT (JSON only):
    """
    raw = agent_model.chat(messages=[{"role": "user", "content": prompt}])
    return safe_json(raw)


def find_value_in_dict(data, target_key):
    """Recursively search for a key in a nested dictionary (case-insensitive)."""
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() == target_key.lower():
                return v
            elif isinstance(v, (dict, list)):
                result = find_value_in_dict(v, target_key)
                if result is not None:
                    return result
    elif isinstance(data, list):
        for item in data:
            result = find_value_in_dict(item, target_key)
            if result is not None:
                return result
    return None


def parse_trap_details(details, agent_model):
    """
    Parses trap details, which can be a dict, a valid JSON string,
    or a broken string requiring LLM intervention.
    """
    if isinstance(details, dict):
        frequency = find_value_in_dict(details, "frequency")
        code = find_value_in_dict(details, "detectioncode")
        if frequency and code:
            return {"frequency": frequency, "code": code}

    if isinstance(details, str):
        json_from_string = safe_json(details)
        if isinstance(json_from_string, dict):
            return parse_trap_details(json_from_string, agent_model)

        logger.info("Trap details is a messy string. Using LLM to parse.")
        return call_trap_parser_llm(agent_model, details)

    return None


# -------------------------------------------------
# 📡 HINT → BLOCKED MOVES (PROGRAMMATIC + SAILING TERMS)
# -------------------------------------------------


def parse_hint_to_blocks(hint: str):
    hint = (hint or "").lower()
    blocked = []

    # Define keywords for directions
    directions = {
        "go": [
            "center",
            "straight",
            "same line",
            "front",
            "forward",
            "bow",
            "ahead",
            "nose",
            "flight line",
            "in front of you",
            "current line",
            "forward line",
            "down the middle",
        ],
        "up": ["left", "port", "edges", "sides"],
        "down": ["right", "starboard", "edges", "sides"],
    }

    # Define keywords for blockages and safe passages
    block_keywords = [
        "occupied",
        "rock",
        "block",
        "blocked",
        "blockage",
        "cannot",
        "obstruction",
        "trouble",
        "obstacle",
        "hazard",
        "threat",
        "stone",
        "chunk",
        "danger",
    ]
    safe_keywords = [
        "clear",
        "safe",
        "empty",
        "open",
        "no obstruction",
        "free",
        "room",
        "nothing blocks",
        "space to slip by",
        "nothing pressing",
        "breathing room",
        "remains quiet",
        "not in front",
        "not toward",
    ]

    # Handle simple cases first
    if "path is clear" in hint or all(
        kw in hint for kw in ["passage", "ahead", "port", "starboard"]
    ):
        return []

    # --- START OF HIGH-CONFIDENCE TRAP RULES ---

    # Liar Trap (Type B.1): Claims 'go' and a side are safe, but the side is a trap.
    # Example: 'Nothing blocks the bow, and port remains quiet. The rock is the thing shadowing the starboard side.'
    if (
        "nothing blocks the bow" in hint
        and "port remains quiet" in hint
        and "starboard" in hint
        and ("rock" in hint or "trouble" in hint)
    ) or (
        "route remains open down the middle" in hint
        and "left side gives you breathing room" in hint
        and "starboard" in hint
        and "rock" in hint
    ):
        blocked.extend(
            ["up", "down"]
        )  # Blocks the explicit rock and the "quiet" trap side.
        logger.info("Liar Trap (Type B.1) detected. Blocking both sides, leaving 'go'.")
        return list(set(blocked))

    # Liar Trap (Type B.2): Uses negation to imply safety, but one is a trap.
    # Example: 'The danger is not in front and not toward starboard. It is posted on the port side of the craft.'
    if (
        "danger is not in front" in hint
        and "not toward starboard" in hint
        and "port" in hint
    ):
        blocked.extend(
            ["up", "down"]
        )  # Blocks explicit danger on port and the "not toward starboard" trap.
        logger.info("Liar Trap (Type B.2) detected. Blocking both sides, leaving 'go'.")
        return list(set(blocked))

    # Liar Trap (Type B.3): Uses "empty space" to imply safety, but one is a trap.
    # Example: 'Your instruments read empty space in front and to the right. The solid threat is beside port.'
    if (
        "empty space in front" in hint
        and ("to the right" in hint or "starboard" in hint)
        and "port" in hint
    ):
        blocked.extend(
            ["up", "down"]
        )  # Blocks explicit threat on port and the "empty space" trap on the right.
        logger.info("Liar Trap (Type B.3) detected. Blocking both sides, leaving 'go'.")
        return list(set(blocked))

    # Liar Trap (Type B.4): Claims one side is open while the other is blocked. Doesn't mention 'go'. The "open" side is the trap.
    # Example: 'The path on your port side stays open... The trouble is sitting off your starboard wing.'
    if "port" in hint and "open" in hint and "starboard" in hint and "trouble" in hint:
        blocked.extend(
            ["up", "down"]
        )  # Blocks the "open" port (trap) and the "trouble" starboard.
        logger.info("Liar Trap (Type B.4) detected. Blocking both sides, leaving 'go'.")
        return list(set(blocked))

    # Ambiguous Open Sides Trap (Type A): Blocks 'go' and claims sides are open, but one is a trap.
    # We only block 'go' and let the defensive logic in pick_move handle the ambiguity.
    ambiguous_sides_keywords = [
        "sides offer space",
        "nothing pressing in from port or starboard",
        "both side paths remain open",
        "dodge either way",
        "sides are open",
        "both side lanes",
    ]
    block_ahead_keywords = [
        "rock is sitting directly in your current line",
        "threat stands on the forward line",
        "ahead is the only place you should not trust",
        "obstruction is directly ahead",
        "rock is on the same line",
        "blockage is straight in front",
    ]
    if any(kw in hint for kw in ambiguous_sides_keywords) and any(
        kw in hint for kw in block_ahead_keywords
    ):
        blocked.append("go")
        logger.info(
            "Ambiguous Open Sides (Type A) trap detected. Blocking 'go' and relying on defensive strategy."
        )
        return list(set(blocked))

    # Keep other specific, high-confidence rules
    if "hazard" in hint and "port" in hint and "nose" in hint and "room" in hint:
        blocked.extend(["up", "down"])
        logger.info(
            "Trap hint 'hazard port, nose room' detected. Blocking 'up' and 'down'."
        )
        return list(set(blocked))

    if "centered and slightly to" in hint:
        if "starboard" in hint:
            if "down" not in blocked:
                blocked.append("down")
        if "port" in hint:
            if "up" not in blocked:
                blocked.append("up")
        logger.info(
            "Trap hint 'centered and slightly to' detected. Blocking the mentioned side."
        )

    # --- END OF HIGH-CONFIDENCE TRAP RULES ---

    # Split hint into sentences or clauses for more granular analysis
    sentences = re.split(r"[.,;!]", hint)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        is_block_sentence = (
            any(kw in sentence for kw in block_keywords) and "nothing" not in sentence
        )

        # Determine which directions are mentioned in the sentence
        mentioned_directions = []
        for move, kws in directions.items():
            if any(kw in sentence for kw in kws):
                mentioned_directions.append(move)
        if is_block_sentence:
            blocked.extend(mentioned_directions)

    return list(set(blocked))


# -------------------------------------------------
# 🚀 MOVE SIMULATION
# -------------------------------------------------


def simulate_move(row, col, move):
    next_col = col + 1
    if move == "up":
        next_row = max(0, row - 1)
    elif move == "down":
        next_row = min(2, row + 1)
    else:
        next_row = row
    return next_row, next_col


# -------------------------------------------------
# 🚀 SAFE MOVE ENGINE (WITH DEFENSIVE LOGIC)
# -------------------------------------------------


def pick_move(current_row, target_row, blocked, hint_text, failures=None):
    # If the exact move failed previously for this hint, block it
    if failures:
        for f in failures:
            if f.get("hint") == hint_text and f.get("move"):
                failed_move = f["move"]
                if failed_move not in blocked:
                    blocked.append(failed_move)
                    logger.warning(
                        f"Blocking move '{failed_move}' due to previous failure with same hint. Reason: {f.get('reason')}"
                    )

    # Define move priorities based on target
    if current_row < target_row:
        candidates = ["down", "go", "up"]
    elif current_row > target_row:
        candidates = ["up", "go", "down"]
    else:
        candidates = ["go", "up", "down"]

    # DEFENSIVE STRATEGY: If the path ahead is blocked, the hint about the sides might be
    # unreliable. Invert the side-move preference to avoid the most "obvious" (and potentially trapped) path.
    if "go" in blocked and len(blocked) < 3:  # Ensure there's a choice to be made
        primary_side_move = candidates[0]
        if primary_side_move in ["up", "down"]:
            # Invert the order of side moves
            secondary_side_move = candidates[2]
            candidates[0], candidates[2] = secondary_side_move, primary_side_move
            logger.warning(
                f"DANGER! 'go' is blocked. Inverting side preference. New candidates: {candidates}"
            )

    logger.info(f"Move candidates (pre-filter): {candidates}")
    for move in candidates:
        if move in blocked:
            logger.warning(f"Move '{move}' is blocked by hint.")
            continue

        if move == "up" and current_row == 0:
            logger.warning(f"Move 'up' is out of bounds at row 0.")
            continue
        if move == "down" and current_row == 2:
            logger.warning(f"Move 'down' is out of bounds at row 2.")
            continue

        return move
    logger.error("Programmatic move picker failed to find a safe move.")
    return None


# -------------------------------------------------
# 🧠 LLM FALLBACK
# -------------------------------------------------


def build_llm_payload(
    current_row, current_col, target_row, hint, blocked_moves=None, failures=None
):
    allowed_moves = ["up", "down", "go"]

    # Remove out of bounds moves
    if current_row == 0 and "up" in allowed_moves:
        allowed_moves.remove("up")
    if current_row == 2 and "down" in allowed_moves:
        allowed_moves.remove("down")

    relevant_failures = []
    if failures:
        relevant_failures = [f for f in failures if f.get("hint") == hint]
        # Strictly remove known fatal moves from allowed_moves
        for f in relevant_failures:
            failed_move = f.get("move")
            if failed_move in allowed_moves:
                allowed_moves.remove(failed_move)

    payload = {
        "state": {
            "current_row": current_row,
            "current_col": current_col,
            "target_row": target_row,
        },
        "allowed_moves": allowed_moves,
        "hint": hint,
    }
    if blocked_moves:
        payload["programmatically_blocked_moves"] = blocked_moves
    if relevant_failures:
        payload["previous_failures"] = relevant_failures
    return payload


def call_llm_fallback(agent_model, payload: dict):
    current_row = payload.get("state", {}).get("current_row", "unknown")
    current_col = payload.get("state", {}).get("current_col", "unknown")
    target_row = payload.get("state", {}).get("target_row", "unknown")
    prompt = f"""
    You are a master rocket navigator avoiding obstacles. Your programmatic logic failed, and you must make a critical decision.

    CRITICAL SURVIVAL RULES:
    1.  **SURVIVAL OVER TARGET**: Your primary goal is to SURVIVE. Moving towards the `target_row` is secondary, UNLESS you are making the final move. Never pick a move that leads to a stone/rock/obstacle.
    2.  **GRID & DESTINATION**: The grid is 3 rows (0, 1, 2) by 12 columns (1-12). You are currently at row {current_row}, column {current_col}. The destination is row {target_row}, column 12. If you are at column 11, your next move is the final one!
    3.  **ANALYZE THE HINT**: The `hint` uses standard or nautical terms.
        - `up` = `left` / `port` (row-1)
        - `down` = `right` / `starboard` (row+1)
        - `go` = `straight` / `ahead` / `bow` / `center` (row unchanged)
    4.  **STAY IN BOUNDS**: You cannot move `up` from row 0 or `down` from row 2.
    5.  **REVIEW BLOCKED MOVES**: `programmatically_blocked_moves` lists directions the parser thinks are blocked. Treat these as deadly unless explicitly disproven.
    6.  **BEWARE OF LIAR TRAPS (CRITICAL)**:
        - If the hint explicitly says one side is blocked (e.g., "chunk off port", "danger beside starboard") AND claims the OTHER side is "safe/empty/friendly", the "SAFE" SIDE IS A TRAP! In this case, BOTH `up` and `down` are deadly. You MUST choose `go`.
        - If the hint says the center/bow/ahead is blocked (e.g., "center is occupied", "bow aimed at a stone"), then `go` is blocked. You must choose a side. If it claims both sides are safe, one is usually a trap! Rely on `previous_failures` to pick the correct safe side.
    7.  **AVOID PREVIOUS FAILURES**: If there is a `previous_failures` array in the input, DO NOT repeat those failed moves. They will crash the rocket again.

    EXAMPLE REASONING:
    Hint: "Port and starboard stay friendly. The bow, however, is aimed right at a stone."
    Previous Failures: [{{"move": "down"}}]
    _thought: "Grid Check: row 1, col 5 (not final). Bounds Check: row 1, all in bounds. Explicit Blocks: bow is aimed at a stone, so 'go' is blocked. Trap Detection: Claims both port and starboard are friendly. One is definitely a trap. Failure Check: 'down' previously failed. Final Candidates: 'go' is blocked, 'down' failed. Must choose 'up'."
    move: "up"

    THINKING PROCESS (Must be strictly followed in `_thought`):
    - Grid Check: Are we at column 11? If yes, we must land on target_row {target_row} if safe.
    - Bounds Check: Which moves are out of bounds?
    - Explicit Blocks: Which moves are explicitly blocked by the hint/programmatic parser?
    - Trap Detection: Is there a liar trap? Which seemingly safe move is actually a trap?
    - Failure Check: Which moves have already failed?
    - Final Candidates: What moves are definitively safe? Pick the best one.

    INPUT:
    {json.dumps(payload, indent=2)}

    OUTPUT (strictly JSON):
    {{
      "_thought": "Grid Check: ..., Bounds Check: ..., Explicit Blocks: ..., Trap Detection: ..., Failure Check: ..., Final Candidates: ...",
      "move": "up|down|go"
    }}
    """
    raw = agent_model.chat(messages=[{"role": "user", "content": prompt}])
    return safe_json(raw)


# -------------------------------------------------
# 🚀 MAIN CONTROLLER
# -------------------------------------------------


class MissionCommander(BaseTask):
    def __init__(self, agent_model, memory: SharedMemory):
        super().__init__(memory.get("task_name"), agent_model, memory)
        self.agent_model = agent_model
        self.memory = memory
        self.rocket = RocketControlAgent(BASE_URL, AGENTS_API_KEY, agent_model)
        self.trap = TrapScannerAgent(BASE_URL, AGENTS_API_KEY, agent_model)
        self.radio = RadioHintAgent(BASE_URL, AGENTS_API_KEY)

    def execute(self):
        game = None
        target_row = None
        move_map = {"up": "left", "down": "right", "go": "go"}

        while True:
            if game is None or (
                isinstance(game, dict) and "lose" in game.get("result", "")
            ):
                logger.info("Starting new game...")
                game = self.rocket.start_game()
                if not game:
                    logger.error("No game response")
                    return
                if isinstance(game, dict):
                    target_row = game.get("base", {}).get("row", 1) - 1

            if not isinstance(game, dict):
                logger.error("Invalid game state")
                return

            player = game.get("player", {})
            current_row = player.get("row", 1) - 1
            current_col = player.get("col", 1)

            logger.info(
                f"Position: row={current_row}, col={current_col}, target={target_row}"
            )

            # KROK 2 & 3: Najpierw odpytaj skaner pułapek i w razie potrzeby rozbrój
            raw_trap_details = self.trap.get_trap_details()
            trap_info = parse_trap_details(raw_trap_details, self.agent_model)

            if trap_info and trap_info.get("frequency") and trap_info.get("code"):
                logger.info(f"Trap detected and parsed: {trap_info}")
                disarm_result = self.trap.disarm_with_data(
                    frequency=trap_info["frequency"], detection_code=trap_info["code"]
                )
                if disarm_result:
                    logger.success("Trap disarmed successfully!")
                else:
                    logger.error(f"Failed to disarm trap. Result: {disarm_result}")
                    return
            else:
                logger.info("No trap detected.")

            # KROK 4: Pobierz wskazówkę radiową
            hint = self.radio.get_hint()
            hint_text = hint.get("hint", "") if isinstance(hint, dict) else (hint or "")
            logger.info(f"Hint: {hint_text}")

            # KROK 5: Przeanalizuj zablokowane ruchy i wykonaj ruch
            blocked_moves = parse_hint_to_blocks(hint_text)

            failures = self.memory.get("failures", [])

            # --- STRICT LEARNING FROM MISTAKES ---
            # Automatically block any move that previously failed for this exact hint
            previous_failed_moves = [
                f.get("move")
                for f in failures
                if f.get("hint") == hint_text and f.get("move")
            ]
            for failed_move in previous_failed_moves:
                if failed_move not in blocked_moves:
                    blocked_moves.append(failed_move)
                    logger.warning(
                        f"Learned from past: explicitly blocking '{failed_move}' which previously failed here."
                    )

            logger.info(f"Programmatically Blocked: {blocked_moves}")

            payload = build_llm_payload(
                current_row, current_col, target_row, hint_text, blocked_moves, failures
            )
            llm_result = call_llm_fallback(self.agent_model, payload)

            move = None
            if isinstance(llm_result, dict):
                move = llm_result.get("move")
                thought = llm_result.get("_thought", "Brak analizy w odpowiedzi LLM.")
                logger.info(f"LLM Analysis (_thought): {thought}")

            # --- BULLETPROOF MISTAKE AVOIDANCE ---
            # If the LLM still picks a failed move (or fails to pick), we override it.
            if move in previous_failed_moves or not move:
                if move in previous_failed_moves:
                    logger.error(
                        f"LLM stubbornly chose previously failed move '{move}'. Overriding!"
                    )

                possible_moves = ["up", "down", "go"]
                if current_row == 0 and "up" in possible_moves:
                    possible_moves.remove("up")
                if current_row == 2 and "down" in possible_moves:
                    possible_moves.remove("down")

                # Try to find a move that hasn't failed and isn't blocked
                safe_candidates = [
                    m
                    for m in possible_moves
                    if m not in previous_failed_moves and m not in blocked_moves
                ]

                # If all unfailed moves are "blocked", we ignore the blocks and just pick one that hasn't failed
                if not safe_candidates:
                    safe_candidates = [
                        m for m in possible_moves if m not in previous_failed_moves
                    ]

                if safe_candidates:
                    move = safe_candidates[0]
                    logger.warning(f"Overrode choice with safe fallback: '{move}'")

            if not move:
                logger.error(
                    "No valid move could be determined by programmatic or LLM approach. Stopping."
                )
                return

            logger.info(f"Chosen move: {move}")

            api_move = move_map[move]
            rocket_move = self.rocket.make_move(api_move)
            if rocket_move.get("error"):
                logger.error("Move failed")
                error_reason = rocket_move.get("error")

                # Store the failure using shared memory
                failures = self.memory.get("failures", [])
                failures.append(
                    {"move": move, "reason": error_reason, "hint": hint_text}
                )
                self.memory.set("failures", failures)
                logger.info(
                    f"Crashed. Remember failure picked move '{move}' for hint '{hint_text}'"
                )

                # A failure likely crashes the rocket, we need a new game loop
                game = None
                continue

            # Uaktualniamy stan na nowy po pomyślnym ruchu
            game = rocket_move
            result_code = game.get("code", "")

            if result_code == 0:
                logger.success("MISSION COMPLETE 🎯")
                return
