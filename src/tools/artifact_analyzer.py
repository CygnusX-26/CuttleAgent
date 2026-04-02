import subprocess

from langchain.tools import tool


@tool
def analyze_artifact(command: list[str]) -> str:
    """
    Analyze an APK file. The following tools are available:
    - `find`
    - `file`
    - `strings`
    - `readelf`
    - `objdump`
    - `nm`
    - `unzip`
    - `aapt`
    - `apktool`
    - `sha256sum`
    """

    try:
        result = subprocess.run(command, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error: {str(e)}"
