# SPDX-License-Identifier: Apache-2.0
# Licensed to the Ed-Fi Alliance under one or more agreements.
# The Ed-Fi Alliance licenses this file to you under the Apache License, Version 2.0.
# See the LICENSE and NOTICES files in the project root for more information.

import os
from edfi_sql_adapter.sql_adapter import Adapter

from sample_data_equity_analysis.connection_parameters import ConnectionParameters

SQL_FILE = "data_prep.sql"


def read_prep_sql_file() -> str:
    with open(os.path.join(os.path.dirname(__file__), SQL_FILE)) as f:
        return f.read()


CREATE_SCHEMA = """
IF NOT EXISTS (
    select 1 from INFORMATION_SCHEMA.SCHEMATA where schema_name = 'edfi_dei'
)
BEGIN
	EXEC('create schema edfi_dei authorization [dbo];');
END
"""

DROP_LEA_STUDENTS = """
IF EXISTS (
	select 1 from INFORMATION_SCHEMA.TABLES where table_schema = 'edfi_dei' and table_name = 'leaStudents'
)
BEGIN
	DROP TABLE edfi_dei.leaStudents
END;
"""

DROP_SCHOOL_STUDENTS = """
IF EXISTS (
	select 1 from INFORMATION_SCHEMA.TABLES where table_schema = 'edfi_dei' and table_name = 'schoolStudents'
)
BEGIN
	DROP TABLE edfi_dei.schoolStudents
END
"""

DROP_SCHEMA = """
DROP SCHEMA edfi_dei;
"""

COUNT_SCHOOL = "SELECT count(1) FROM analytics.StudentSchoolDemographicsBridge"
COUNT_LEA = "SELECT count(1) FROM analytics.StudentLocalEducationAgencyDemographicsBridge"

def run_prep_file(adapter: Adapter) -> None:
    """
    Installs temporary tables in the `edfi_dei` schema.

    Parameters
    ----------
    adapter: Adapter
        An MSSQL adapter
    """
    adapter.execute_script(
        [CREATE_SCHEMA, DROP_LEA_STUDENTS, DROP_SCHOOL_STUDENTS, read_prep_sql_file()]
    )


def cleanup_database(adapter: Adapter) -> None:
    """
    Deletes temporary tables and the `edfi_dei` schema itself.

    Parameters
    ----------
    adapter: Adapter
        An MSSQL adapter
    """
    adapter.execute_script([DROP_LEA_STUDENTS, DROP_SCHOOL_STUDENTS, DROP_SCHEMA])

def get_school_demographics_count(adapter: Adapter) -> int:
    """
    Gets the count of all School Demographics rows.

    Parameters
    ----------
    adapter: Adapter
        An MSSQL adapter
    """
    return adapter.get_int(COUNT_SCHOOL)

def get_lea_demographics_count(adapter: Adapter) -> int:
    """
    Gets the count of all Local Education Agency Demographics rows.

    Parameters
    ----------
    adapter: Adapter
        An MSSQL adapter
    """
    return adapter.get_int(COUNT_LEA)
