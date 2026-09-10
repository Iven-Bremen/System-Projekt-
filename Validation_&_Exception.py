Return = (False," only CVS is allowed")

import csv
from enum import Enum
from pathlib import Path

class File_Validation(Enum):
    true = (True, 'passt')
    false = (False, 'nah')

class Category(Enum):
    OsTech = 1

class Category(Enum):
    OsTech = 1
    SR830 = 2

class TAG(Enum):
    OsTech = 1

class State(Enum):
    SUCCESS = "S"
    FAIL = "F"
    RUNNING = "R"
    WARNING = "W"
    ERROR = "E"

ERWARTETE_HEADER = [
    "Date", "Time", "Ms", "Category", "Tag", "State",
    "Message", "Value", "Info", "AdditionalMessage",
    "AdditionalValue", "AdditionalInfo", "Else"
]

def pruefe_csv(dateipfad):
    with open(dateipfad, mode="r", encoding="utf-8") as file:
        # HINWEIS: Falls deine Datei mit Semikolon getrennt ist, setze delimiter=";"
        reader = csv.reader(file, delimiter=",")
        aktuelle_header = next(reader)


"""
def header_sollte_passen(file_path: str) -> tuple[bool, str]:
    path = Path(file_path)

    if path.suffix.lower() != ".csv":
        return False, "Only CSV is allowed"

    if not path.exists():
        return False, f"File does not exist: {file_path}"
"""

# print(File_Validation.true.value[0])
# print(File_Validation.true.value[1])