from pathlib import Path

import pandas as pd

from exporter import export_workbook
from models import OperationData, StreamData


def test_export_workbook(tmp_path: Path) -> None:
    output = tmp_path / "out.xlsx"
    export_workbook(
        str(output),
        [StreamData("Feed", 25.0, 101.325, 100.0, 1600.0, {"Methane": 0.9})],
        [OperationData("V-100", "Separator", True)],
    )
    assert output.exists()
    assert set(pd.ExcelFile(output).sheet_names) == {"Streams", "Composition", "Operations"}

