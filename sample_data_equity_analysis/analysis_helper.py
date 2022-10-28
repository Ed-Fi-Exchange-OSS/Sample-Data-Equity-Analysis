# SPDX-License-Identifier: Apache-2.0
# Licensed to the Ed-Fi Alliance under one or more agreements.
# The Ed-Fi Alliance licenses this file to you under the Apache License, Version 2.0.
# See the LICENSE and NOTICES files in the project root for more information.

import math
from typing import Tuple

import pandas as pd
import scipy.stats
import seaborn as sns
import matplotlib.pyplot as plt
from numpy import NaN
import textwrap

from sample_data_equity_analysis.utilities import (
    log_info,
    log_error,
    log_warning,
    log_message,
    num_to_string,
    log_dataframe,
)

MAGIC_NUMBER = 30


def run_anova(students: pd.DataFrame, demographic: str, measure_label: str) -> bool:
    """
    Runs ANOVA analysis for the given demographic and statistic, used when there
    are more than two categories / classifications for the demographic.

    Parameters
    ----------
    students: DataFrame
        Must have been created from data loaded by the accompanying SQL script
    demographic: str
        The demographic to analyze
    measure_label: str
        The measure label to analyze
    """

    not_null = students[measure_label].notna()

    # Test that variances are close enough for running ANOVA
    variances_all = (
        students[not_null]
        .groupby(by=[demographic], as_index=False)
        .agg({measure_label: "var", "StudentKey": "count"})
    )

    # Only explore those categories with > MAGIC_NUMBER data points
    included = variances_all[(variances_all["StudentKey"] > MAGIC_NUMBER)]

    if included.shape[0] < 2:
        log_error(
            f"""Cannot run this ANOVA test because there are not enough populations
with size greater than {MAGIC_NUMBER}."""
        )
        return False

    excluded = variances_all[(variances_all["StudentKey"] <= MAGIC_NUMBER)][
        demographic
    ].unique()
    if len(excluded) > 0:
        log_warning(
            f"""ANOVA test will exclude these categories because they have a
population size of less than {MAGIC_NUMBER}, although they will
still appear in the boxplot for visual inspection: {excluded}."""
        )

    # ANOVA
    labels = pd.unique(included[demographic].values)

    stat_by_demographic = {
        label: students[(students[demographic] == label) & not_null][measure_label]
        for label in labels
    }
    data = stat_by_demographic.values()
    _stat, p_value = scipy.stats.f_oneway(*data)

    if p_value == NaN:
        log_warning(
            "The differences in variance / standard deviation are too great for "
            "ANOVA (homoscedasticity violation). Trying Kruskal-Wallis instead."
        )
        _stat, p_value = scipy.stats.kruskal(*data)

    log_message(
        f"Hypothesis: the difference in {measure_label} by {demographic} is not statistically significant."
    )
    if p_value > 0.05:
        log_info(
            f"Hypothesis upheld: difference is not significant. P value: {num_to_string(p_value)}"
        )
    else:
        log_error(
            f"Hypothesis rejected: there is a significant difference. P value: {num_to_string(p_value)}"
        )

        tukey = scipy.stats.tukey_hsd(*data)

        # Trying to build a markdown table that would be interpreted correctly
        # by Jupyter was proving difficult. Gave up and switched to a simpler
        # DataFrame rendering approach.
        columns = [
            "Label 1",
            "Label 2",
            "Stat",
            "p Value",
            "Low CI",
            "High CI",
            "Effect Size",
        ]
        rows = []

        conf_interval = tukey.confidence_interval()
        for i in range(len(labels)):
            for j in range(len(labels)):
                if i >= j:  # comparing to self
                    continue
                stat = num_to_string(tukey.statistic[i][j])
                p = num_to_string(tukey.pvalue[i][j])
                low = num_to_string(conf_interval.low[i][j])
                high = num_to_string(conf_interval.high[i][j])
                effect_size = _calc_cohens_d(
                    stat_by_demographic[labels[i]], stat_by_demographic[labels[j]]
                )
                rows.append([labels[i], labels[j], stat, p, low, high, effect_size])

        tukey_output = pd.DataFrame(columns=columns, data=rows)
        tukey_output.sort_values(by=["p Value"], inplace=True)
        log_dataframe(tukey_output)

    return True


def _calc_cohens_d(sample_1: pd.Series, sample_2: pd.Series) -> Tuple[str, str]:
    """
    This assumes independent samples, and thus is only appropriate for student data when:

    (a) comparing within one demographic, and
    (b) there are mutually exclusive categories for that demographic

    For example, it would not be appropriate to use this in comparing Hispanic/Latino Ethnicity
    to Sex, because these are not independent. It would also not be appropriate with race,
    since one student can have multiple race associations.

    Parameters
    ----------
    sample_1: Series
        Sample 1 of 2 for comparison
    sample_2: Series
        Sample 2 of 2 for comparison

    Returns
    -------
    Tuple: (str, str)
        The first value is the effect size as a number, and the second is a text description of the impact
    """
    n1 = sample_1.count()
    m1 = sample_1.mean()
    s1 = sample_1.std()

    n2 = sample_2.count()
    m2 = sample_2.mean()
    s2 = sample_2.std()

    s = math.sqrt(((n1 - 1) * (s1**2) + (n2 - 1) * (s2**2)) / (n1 + n2 - 2))
    d = (abs(m1 - m2)) / s

    effect_size = "Very small"
    if d > 0.01 and d <= 0.2:
        effect_size = "Small"
    elif d <= 0.5:
        effect_size = "Medium"
    elif d <= 0.8:
        effect_size = "Large"
    elif d <= 1.20:
        effect_size = "Very large"
    else:
        effect_size = "Huge"

    return (num_to_string(d), effect_size)


def run_t_test(
    students: pd.DataFrame,
    demographic: str,
    measure_label: str,
) -> bool:
    """
    Runs Welch's t-test analysis for the given demographic and statistic, used
    when there are two categories / classifications for the demographic.

    Parameters
    ----------
    students: DataFrame
        Must have been created from data loaded by the accompanying SQL script
    demographic: str
        The demographic to analyze
    measure_label: str
        The measure label to analyze
    """

    not_null = students[measure_label].notna()

    # Only explore those categories with > MAGIC_NUMBER data points
    grouped = students[not_null].groupby(by=[demographic], as_index=False)

    group_count = grouped.count()
    categories = group_count[(group_count["StudentKey"] > MAGIC_NUMBER)][
        demographic
    ].unique()

    if len(categories) < 2:
        query = group_count["StudentKey"] <= MAGIC_NUMBER
        log_error(
            f"Cannot run this t-test because one or both categories have a "
            f"population size of less than {MAGIC_NUMBER}: "
            f"{group_count[query][demographic].unique()}"
        )
        return False

    cat_0 = students[(students[demographic] == categories[0]) & not_null][measure_label]
    cat_1 = students[(students[demographic] == categories[1]) & not_null][measure_label]

    _stat, p_value = scipy.stats.ttest_ind(cat_0, cat_1, equal_var=False)

    log_message(
        f"Hypothesis: the difference in {measure_label} for {demographic} is not statistically significant."
    )
    if p_value > 0.05:
        log_info(
            f"Hypothesis upheld: difference is not significant. P value: {num_to_string(p_value)}"
        )
    else:
        log_error(
            f"Hypothesis rejected: there is a significant difference. P value: {num_to_string(p_value)}"
        )

        cohens_d = _calc_cohens_d(cat_0, cat_1)
        log_warning(f"Effect size: {cohens_d[0]}, {cohens_d[1]}")

    cat_0_stats = cat_0.describe()
    cat_1_stats = cat_1.describe()
    stats = pd.DataFrame(
        columns=["Label", "Count", "Mean", "StD", "Min", "Max"],
        data=[
            [
                categories[0],
                num_to_string(cat_0_stats["count"]),
                num_to_string(cat_0_stats["mean"]),
                num_to_string(cat_0_stats["std"]),
                num_to_string(cat_0_stats["max"]),
                num_to_string(cat_0_stats["min"]),
            ],
            [
                categories[1],
                num_to_string(cat_1_stats["count"]),
                num_to_string(cat_1_stats["mean"]),
                num_to_string(cat_1_stats["std"]),
                num_to_string(cat_1_stats["max"]),
                num_to_string(cat_1_stats["min"]),
            ],
        ],
    )
    log_dataframe(stats)

    return True


def create_box_plots(
    students: pd.DataFrame,
    demographic: str,
    measure: str,
    title: str,
) -> None:
    """
    Creates a single diagram with box plots for each distinct category in the
    demographic.

    Parameters
    ----------
    students: DataFrame
        Must have been created from data loaded by the accompanying SQL script
    demographic: str
        The demographic to analyze
    measure_label: str
        The measure label to analyze
    title: str
        Chart title
    """
    labels = students[demographic].drop_duplicates().sort_values()

    plot_params = {
        "data": students,
        "kind": "box",
        "y": measure,
        "height": 5,
        "aspect": 2,
        "showmeans": True,
        "meanprops": {
            "markersize": "10",
            "markerfacecolor": "white",
            "markeredgecolor": "black",
            "marker": "o",
        },
    }
    _ = sns.catplot(x=demographic, order=labels, **plot_params)
    plt.title(title, fontsize=14)
    wrap_labels(plt)

    plt.show()


def wrap_labels(plt: plt.plot) -> None:
    """
    Improve x-axis labels with line wrapping. Courtesy of
    https://medium.com/dunder-data/automatically-wrap-graph-labels-in-matplotlib-and-seaborn-a48740bc9ce

    Parameters
    ----------
    plt: plot
        A Matlib plot
    """
    ax = plt.gca()

    labels = []
    for label in ax.get_xticklabels():
        text = label.get_text()
        labels.append(textwrap.fill(text, width=20, break_long_words=True))
    ax.set_xticklabels(labels, rotation=45)
