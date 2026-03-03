import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent

def get_system_guidelines() -> str:
    """Read and return the universal AI system guidelines from disk.

    Returns:
        str: Full contents of "config/system_guidelines.txt".
    """
    with open(BACKEND_DIR / "config/system_guidelines.txt", "r") as f:
        guidelines = f.read()

    return guidelines

def get_ai_instructions() -> str:
    """Read and return the AI instruction template from disk.

    Returns:
        str: Full contents of "config/instructions.txt".
    """
    with open(BACKEND_DIR / "config/instructions.txt", "r") as f:
        instructions = f.read()

    return instructions

def get_ai_requirements() -> dict:
    """Load and return AI requirement definitions from JSON configuration.

    Returns:
        dict: Parsed JSON object from "config/requirements.json".
    """

    with open(BACKEND_DIR / "config/requirements.json", "r") as f:
        requirements = json.load(f)

    return requirements

def set_ai_instructions(new_instructions: str | None = None) -> tuple[bool, str]:
    """Persist updated AI instructions to configuration storage.

    Args:
        new_instructions (str | None): New instruction text to write. When
            "None", no file change is made.

    Returns:
        tuple[bool, str]: Success flag and status message.
    """
    # Update Instructions if provided
    if new_instructions is not None:
        instr_path = BACKEND_DIR / "config/instructions.txt"
        with open(instr_path, "w") as f:
            f.write(new_instructions)
            
    return True, "Settings updated successfully."

def set_ai_requirements(new_requirements: dict | str | None = None) -> tuple[bool, str]:
    """Persist updated AI requirement definitions to JSON configuration.

    Args:
        new_requirements (dict | str | None): Requirement payload to save. If a
            string is provided, it must be valid JSON.

    Returns:
        tuple[bool, str]: Success flag and status message. Returns "False"
        with an error message when JSON parsing fails.
    """
    # Update Requirements if provided
    if new_requirements is not None:
        req_path = BACKEND_DIR / "config/requirements.json"
        
        # Verify it is valid JSON before writing to disk
        if isinstance(new_requirements, str):
            try:
                new_requirements = json.loads(new_requirements)
            except json.JSONDecodeError:
                return False, "Invalid JSON format provided."

        with open(req_path, "w") as f:
            json.dump(new_requirements, f, indent=4)
    return True, "Settings updated successfully."

def get_threshold_settings():
    """Read pass/fail threshold settings with safe defaults.

    Returns:
        dict: Threshold settings containing "pass_threshold" and
        "fail_threshold". Defaults to "80" and "50" if file is missing or
        unreadable.
    """
    settings_path = BACKEND_DIR / "config/settings.json"
    
    defaults = {"pass_threshold": 80, "fail_threshold": 50}
    
    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return defaults
    return defaults

def set_threshold_settings(pass_val, fail_val):    
    """Save pass/fail threshold settings to configuration JSON.

    Args:
        pass_val (int | float): Score threshold considered a pass.
        fail_val (int | float): Score threshold considered a fail.

    Returns:
        tuple[bool, str]: Success flag and status message. Returns "False"
        when writing fails.
    """
    settings_path = BACKEND_DIR / "config/settings.json"
    
    settings_data = {
        "pass_threshold": pass_val,
        "fail_threshold": fail_val
    }
    
    try:
        # Ensure the backend directory exists
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, "w") as f:
            json.dump(settings_data, f, indent=4)
        return True, "Thresholds saved."
    except Exception as e:
        return False, f"Error saving thresholds: {str(e)}"