from __future__ import annotations

from pathlib import Path

import pandas as pd

from models import OperationData, StreamData


def export_workbook(
    path: str,
    streams: list[StreamData],
    operations: list[OperationData],
) -> Path:
    destination = Path(path)
    stream_rows = [
        {
            "Name": item.name,
            "Temperature": item.temperature,
            "Pressure": item.pressure,
            "Molar Flow": item.molar_flow,
            "Mass Flow": item.mass_flow,
        }
        for item in streams
    ]
    composition_rows = [
        {"Stream": stream.name, "Component": name, "Mole Fraction": value}
        for stream in streams
        for name, value in stream.composition.items()
    ]
    operation_rows = [
        {"Name": item.name, "Type": item.operation_type, "Solved": item.is_solved}
        for item in operations
    ]
    with pd.ExcelWriter(destination, engine="openpyxl") as writer:
        pd.DataFrame(stream_rows).to_excel(writer, sheet_name="Streams", index=False)
        pd.DataFrame(composition_rows).to_excel(writer, sheet_name="Composition", index=False)
        pd.DataFrame(operation_rows).to_excel(writer, sheet_name="Operations", index=False)
    return destination

