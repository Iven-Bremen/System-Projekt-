Return = (False," only CVS is allowed")

import csv
import Log
from enum import Enum
from pathlib import Path

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
    VALIDATION = "V"

class File_Validation(Enum):
    Valid_CVS       =           (True,      'Datei ist eine gueltige CSV-Datei und kann importiert werden.'         , ""  )
    Is_NO_CVS       =           (False,     'Der Header ist gueltig, aber die Datei hat keine CSV-Endung.'          , ""  )
    Is_Valid        =           (False,     'Die Datei hat eine CSV-Endung, aber der Header ist ungueltig.'         , ""  )
    Is_Invalid      =           (False,     'Die Datei hat weder eine CSV-Endung noch den erwarteten Header.'       , ""  )
    No_File         =           (False,     'Keine Datei Ausgewählt.'                                               , ""  )


ERWARTETE_HEADER = [
    "Date", "Time", "Ms", "Category", "Tag", "State",
    "Message", "Value", "Info", "AdditionalMessage",
    "AdditionalValue", "AdditionalInfo", "Else"
]
def pruefe_csv(dateipfad):
    Log.Log(
        Category="CSV",
        TAG="IMPORT",
        State=State.VALIDATION,
        Message="File Path",
        Value=str(dateipfad),
        Info="Dateipfad des CVS Datei",
    )
    with open(dateipfad, mode="r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file, delimiter=",")
        return next(reader, []) == ERWARTETE_HEADER

def Check_CVS_Import(dateipfad):
    """Prueft Dateityp und Header und protokolliert das Enum-Ergebnis."""
    path = Path(dateipfad)
    is_csv = path.suffix.lower() == ".csv"
    has_valid_header = False

    if path.is_file():
        try:
            has_valid_header = pruefe_csv(path)
        except (OSError, UnicodeError, csv.Error):
            has_valid_header = False

    if is_csv and has_valid_header:
        ergebnis = File_Validation.Valid_CVS
    elif not is_csv and has_valid_header:
        ergebnis = File_Validation.Is_NO_CVS
    elif is_csv and not has_valid_header:
        ergebnis = File_Validation.Is_Valid
    else:
        ergebnis = File_Validation.Is_Invalid

    Log.Log(
        Category="CVS",
        TAG="IMPORT",
        State=State.VALIDATION,
        Message="CVS Check",
        Value=ergebnis.value[1],
        Info="CONTINUE" if ergebnis.weiter_fuehren else "STOP",
    )
    return ergebnis