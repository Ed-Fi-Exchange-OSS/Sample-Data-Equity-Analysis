# SPDX-License-Identifier: Apache-2.0
# Licensed to the Ed-Fi Alliance under one or more agreements.
# The Ed-Fi Alliance licenses this file to you under the Apache License, Version 2.0.
# See the LICENSE and NOTICES files in the project root for more information.

import os
from typing import Any, Callable, Optional
from IPython.display import display, Markdown, HTML
import ipywidgets as widgets

from edfi_sql_adapter.sql_adapter import (
    Adapter,
    create_mssql_adapter_with_integrated_security,
    create_mssql_adapter,
)

from sample_data_equity_analysis.connection_parameters import ConnectionParameters
from sample_data_equity_analysis.data_prep import run_prep_file, cleanup_database
from sample_data_equity_analysis.utilities import (
    log_info,
    log_error,
    log_message,
    Constants,
)
from sample_data_equity_analysis.analysis import run_analysis

adapter: Optional[Adapter] = None


def _get_spinner() -> widgets.Widget:
    with open("spinner.png", "rb") as f:
        img = f.read()

        return widgets.Image(value=img)


def _get_db_adapter(params: Optional[ConnectionParameters] = None) -> Adapter:
    global adapter

    if params is None:
        if adapter is None:
            raise RuntimeError("Adapter has not been initialized yet.")
        return adapter

    if params.username.strip() == "":
        adapter = create_mssql_adapter_with_integrated_security(
            params.server,
            params.database,
            int(params.port or "1433"),
            params.encrypt,
            params.trust_certificate,
        )
    else:
        adapter = create_mssql_adapter(
            params.username,
            os.getenv("MSSQL_PASSWORD") or "",
            params.server,
            params.database,
            int(params.port or "1433"),
            params.encrypt,
            params.trust_certificate,
        )

    return adapter


def _attach_on_prepare_click(
    controls: dict[str, widgets.Widget]
) -> Callable[[Any], None]:
    def __on_prepare_click(b) -> None:
        output: widgets.Output = controls[Constants.OUTPUT]
        with output:
            output.clear_output()
            display(_get_spinner())
            output.clear_output(wait=True)

            adapter = _get_db_adapter(
                ConnectionParameters(
                    controls[Constants.SERVER].value,
                    controls[Constants.PORT].value,
                    controls[Constants.DATABASE].value,
                    controls[Constants.ENCRYPT].value,
                    controls[Constants.TRUST].value,
                    controls[Constants.USERNAME].value,
                    os.getenv("DEI_DB_PASSWORD") or "",
                )
            )

            if bool(controls[Constants.INSTALL_TABLES].value):
                try:
                    run_prep_file(adapter)

                    log_info("Ready to go.")
                except Exception as err:
                    log_error("Error occurred:")
                    log_message(f"```{err}```")
            else:
                log_info("Ready to go")

    return __on_prepare_click


def _attach_on_run_click(controls: dict[str, widgets.Widget]) -> Callable[[Any], None]:
    def __on_run_click(b: Any) -> None:
        ed_org_level = controls[Constants.ED_ORG].value
        measure = controls[Constants.MEASURE].value

        run_analysis(_get_db_adapter(), ed_org_level, measure)

    return __on_run_click


def _attach_on_cleanup_click(output: widgets.Output) -> Callable[[Any], None]:
    def __on_cleanup_click(b: Any) -> None:
        with output:
            output.clear_output()
            display(_get_spinner())
            output.clear_output(wait=True)

            try:
                cleanup_database(_get_db_adapter())
                log_info("Clean complete.")
            except Exception as err:
                log_error("Error occurred:")
                log_message(f"```{err}```")

    return __on_cleanup_click


def setup_database_prep() -> None:
    log_message("## Prepare Database for Analysis")
    log_message(
        "Enter database connectivity information below and click the Prepare button "
        "to setup an `edfi_dei` schema and two new tables. ❗❗ This will fail if you "
        "have not install the required Analytics Middle Tier components."
    )
    display(
        HTML(
            f"""
<details>
<summary>▶ <span style="color: blue">Help for database settings</span></summary>
<p>For Windows integrated security, leave the username blank. The password can only
be set by environment variable. All of the fields can be controlled by environmental
variables: simply set the variables before starting up Jupyter. The available variables
are:</p>
<ul>
<li>DEI_SERVER</li>
<li>DEI_PORT</li>
<li>DEI_DATABASE</li>
<li>DEI_USERNAME</li>
<li>DEI_PASSWORD</li>
<li>DEI_ENCRYPT</li>
<li>DEI_TRUST_CERTIFICATE</li>
</ul>
</details>
"""
        )
    )
    server = widgets.Text(value=os.getenv(Constants.DEI_SERVER), description="Server:")
    port = widgets.Text(value=os.getenv(Constants.DEI_PORT), description="Port:")
    database = widgets.Text(
        value=os.getenv(Constants.DEI_DATABASE), description="Database:"
    )
    username = widgets.Text(
        value=os.getenv(Constants.DEI_USERNAME), description="Username:"
    )
    encrypt = widgets.Checkbox(
        value=bool(os.getenv(Constants.DEI_ENCRYPT)),
        description="Use encrypted connection",
        indented=True,
    )
    trust = widgets.Checkbox(
        value=bool(os.getenv(Constants.DEI_TRUST_CERTIFICATE)),
        description="Trust self-signed certificate",
        indented=True,
    )
    install = widgets.Checkbox(
        value=False, description="Install equity analysis tables", indented=True
    )

    prepare = widgets.Button(
        description="Prepare database connection", button_style="primary"
    )

    output = widgets.Output()
    display(server, port, database, username, encrypt, trust, install, prepare, output)

    controls = dict()
    controls[Constants.SERVER] = server
    controls[Constants.PORT] = port
    controls[Constants.DATABASE] = database
    controls[Constants.USERNAME] = username
    controls[Constants.ENCRYPT] = encrypt
    controls[Constants.TRUST] = trust
    controls[Constants.OUTPUT] = output
    controls[Constants.INSTALL_TABLES] = install

    prepare.on_click(_attach_on_prepare_click(controls))


def setup_analysis_options() -> None:
    log_message("## Choose What to Analyze")
    ed_org = widgets.RadioButtons(
        options=[Constants.SCHOOL, Constants.LEA], description="Student relationship:"
    )
    measure = widgets.RadioButtons(
        options=[
            Constants.ATTENDANCE,
            Constants.BEHAVIOR,
            Constants.COURSE_PERFORMANCE,
        ],
        description="Measure:",
    )
    run = widgets.Button(description="Run analysis", button_style="primary")

    output = widgets.Output()

    display(ed_org, measure, run, output)

    controls = dict()
    controls[Constants.ED_ORG] = ed_org
    controls[Constants.MEASURE] = measure
    controls[Constants.OUTPUT] = output

    run.on_click(_attach_on_run_click(controls))


def setup_cleanup() -> None:
    log_message("## Cleanup")
    log_message(
        "Click the button below to remove the two temporary tables, `edfi_dei.leaStudents` "
        "and `edfi_dei.schoolStudents`. If you have not finished running all of the desired "
        "analyses, then it may be preferable to skip this step. Once you have run this, you "
        "must select the 'Install equity analysis tables' option to re-install the tables."
    )
    cleanup = widgets.Button(description="Cleanup the database", button_style="primary")

    output = widgets.Output()
    display(cleanup, output)

    cleanup.on_click(_attach_on_cleanup_click(output))
