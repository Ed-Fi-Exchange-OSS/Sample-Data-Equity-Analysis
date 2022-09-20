# SPDX-License-Identifier: Apache-2.0
# Licensed to the Ed-Fi Alliance under one or more agreements.
# The Ed-Fi Alliance licenses this file to you under the Apache License, Version 2.0.
# See the LICENSE and NOTICES files in the project root for more information.

from typing import Union

from IPython.display import display, Markdown
import pandas as pd


def log_message(message: str) -> None:
    display(Markdown(message))


def log_info(message: str) -> None:
    display(Markdown(f"✅ **{message}**"))


def log_warning(message: str) -> None:
    display(Markdown(f"❕ **{message}**"))


def log_error(message: str) -> None:
    display(Markdown(f"❌ **{message}**"))


def log_dataframe(df: pd.DataFrame) -> None:
    log_message(df.to_markdown(index=False))


def num_to_string(number: Union[int, float]) -> str:
    return "{:,}".format(round(number, 3))


class Constants:
    SERVER = "server"
    PORT = "port"
    DATABASE = "database"
    USERNAME = "username"
    ENCRYPT = "encrypt"
    TRUST = "trust"
    OUTPUT = "output"
    DEI_SERVER = "DEI_SERVER"
    DEI_PORT = "DEI_PORT"
    DEI_DATABASE = "DEI_DATABASE"
    DEI_USERNAME = "DEI_USERNAME"
    DEI_PASSWORD = "DEI_PASSWORD"
    DEI_ENCRYPT = "DEI_ENCRYPT"
    DEI_TRUST_CERTIFICATE = "DEI_TRUST_CERTIFICATE"
    ED_ORG = "Education Organization"
    MEASURE = "Measure"
    SCHOOL = "School"
    LEA = "Local Education Agency"
    ATTENDANCE = "Attendance Rate"
    BEHAVIOR = "Behavior"
    COURSE_PERFORMANCE = "Course Performance"
    INSTALL_TABLES = "Install tables"
