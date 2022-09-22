# SPDX-License-Identifier: Apache-2.0
# Licensed to the Ed-Fi Alliance under one or more agreements.
# The Ed-Fi Alliance licenses this file to you under the Apache License, Version 2.0.
# See the LICENSE and NOTICES files in the project root for more information.

import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats
import seaborn as sns
from IPython.display import display
import ipywidgets as widgets

from edfi_sql_adapter.sql_adapter import Adapter

from sample_data_equity_analysis.utilities import (
    log_info,
    log_error,
    log_warning,
    log_message,
    num_to_string,
)
from sample_data_equity_analysis.analysis_helper import (
    run_anova,
    create_box_plots,
    run_t_test,
)
from sample_data_equity_analysis.utilities import Constants

GET_LEA_STUDENTS = "select * from edfi_dei.leaStudents"
GET_SCHOOL_STUDENTS = "select * from edfi_dei.schoolStudents"
MEASURE_ATTENDANCE = "AttendanceRate"
MEASURE_DISCIPLINE = "NumberDisciplineIncidents"
MEASURE_COURSE_PERF = "AverageGrade"

DEMOGRAPHIC_RACE = "Race"
DEMOGRAPHIC_LATINX = "IsHispanic"
DEMOGRAPHIC_ENGLISH = "LimitedEnglishProficiency"
DEMOGRAPHIC_SEX = "Sex"
DEMOGRAPHIC_DISABILITY = "Disability"
DEMOGRAPHIC_LANGUAGE = "Language"
DEMOGRAPHIC_TRIBAL = "TribalAffiliation"

def _get_lea_students(adapter: Adapter) -> pd.DataFrame:
    return pd.read_sql(GET_LEA_STUDENTS, adapter.engine.connect())


def _get_school_students(adapter: Adapter) -> pd.DataFrame:
    return pd.read_sql(GET_SCHOOL_STUDENTS, adapter.engine.connect())


def _prepare_for_charts() -> None:
    plt.style.use("ggplot")
    sns.set_theme(style="darkgrid")

def _exec_anova(
    students: pd.DataFrame, demographic: str, measure_label: str, measure: str
) -> None:
    log_message(f"### {measure}")
    output = widgets.Output()
    display(output)
    with output:
        t = run_anova(students, demographic, measure_label)
        if t:
            create_box_plots(students, demographic, measure_label, measure)


def _exec_t_test(
    students: pd.DataFrame, demographic: str, measure_label: str, measure: str
) -> None:
    log_message(f"### {measure}")
    output = widgets.Output()
    display(output)
    with output:
        t = run_t_test(students, demographic, measure_label)
        if t:
            create_box_plots(students, demographic, measure_label, measure)


def _run_detailed_analysis(
    students: pd.DataFrame, measure: str, measure_label: str
) -> None:
    _exec_anova(students, DEMOGRAPHIC_RACE, measure_label, f"{measure} by Race")
    _exec_t_test(
        students,
        DEMOGRAPHIC_LATINX,
        measure_label,
        f"{measure} by Hispanic/Latino Ethnicity",
    )
    _exec_t_test(
        students,
        DEMOGRAPHIC_ENGLISH,
        measure_label,
        f"{measure} by English Proficiency",
    )
    # TODO notebook needs to state assumptions about different demographics in the Ed-Fi sample
    # data set; for example, it does not distinguish between gender and sex. In fact there
    # are historically only two sexes in the sample data (before Data Standard 4). In that
    # sense a t_test would be more appropriate. However, this will be an ANOVA because other
    # data sets can have additional sex type descriptor values.
    _exec_anova(students, DEMOGRAPHIC_SEX, measure_label, f"{measure} by Sex/Gender")
    _exec_anova(
        students, DEMOGRAPHIC_DISABILITY, measure_label, f"{measure} by Disability"
    )
    _exec_anova(students, DEMOGRAPHIC_LANGUAGE, measure_label, f"{measure} by Language")
    _exec_anova(
        students, DEMOGRAPHIC_TRIBAL, measure_label, f"{measure} by Tribal Affiliation"
    )


def _run_big_picture(students: pd.DataFrame, measure: str, measure_label: str) -> None:
    log_message(
        f"""The following chart contains a histogram of the {measure} for the entire student body,
with an overlay of the
[kernel density estimation](https://en.wikipedia.org/wiki/Kernel_density_estimation)
curve for the sample distribution."""
    )

    output = widgets.Output()
    display(output)
    with output:
        sns.displot(data=students, x=measure_label, kde=True)
        plt.show()

    log_message(
        """Below, we will visually inspect relationships with the help of box plots and
then look at T-test (comparing two samples) and ANOVA (comparing more than two
samples) results to help determine if there are statistically significant
differences between the results for different populations. These tests are
appropriate when:

* Samples are independent (groups are mutually exclusive)
* Normal looking: sample size >= 30, or p > 0.05 in a test of normality
* For ANOVA, variances should be "equal". The analysis will reject
  the standard one-way ANOVA if there is too much variation in variances / standard
  deviations. In that case, we will turn to the Kruskal-Wallis test.
  * Both test types, Anova and Kruskal-Wallis, will use 0.05 as the significance
    level when evaluating the p-value result.
* The T-test will be calculated using Welch's test, which accounts for unequal
  variances.

ANOVA tests will show _that there are differences_ without specifying _which_
samples standout from the group. For that, we will perform _post hoc_ analysis
using [Tukey's method](https://statisticsbyjim.com/anova/post-hoc-tests-anova/).

For both the T-Test and ANOVA, when the null hypothesis is not supported,
the notebook will calculate [Cohen's D](https://en.wikipedia.org/wiki/Effect_size#Cohen's_d)
to give a sense of the overall effect size."""
    )


def run_analysis(adapter: Adapter, ed_org_level: str, measure: str) -> None:
    """
    Orchestrates execution of the designated analysis.

    Parameters
    ----------
    adapter: Adapter
        An MSSQL adapter
    ed_org_level: str
        Either "school" or "Lea"
    measure: str
        The measure to calculate, e.g Course Performance or Attendance Rate, etc.
    """
    _prepare_for_charts()

    try:
        students = (
            _get_school_students(adapter)
            if ed_org_level == Constants.SCHOOL
            else _get_lea_students(adapter)
        )
    except Exception as err:
        log_error(f"Could not load initial data set:")
        log_message(f"```{err}```")
        return

    measure_label: str = ""

    if measure == Constants.ATTENDANCE:
        measure_label = MEASURE_ATTENDANCE
    elif measure == Constants.BEHAVIOR:
        measure_label = MEASURE_DISCIPLINE
    elif measure == Constants.COURSE_PERFORMANCE:
        measure_label = MEASURE_COURSE_PERF
    else:
        log_error("Invalid measure selection.")
        return

    log_message(f"## {measure} Analysis for {ed_org_level}s")
    _run_big_picture(students, measure, measure_label)
    _run_detailed_analysis(students, measure, measure_label)
