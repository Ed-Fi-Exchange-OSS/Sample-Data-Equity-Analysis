# Ed-Fi Sample Data Equity Analysis

## Goal

The Ed-Fi Alliance's sample data sets have realistic but fictional names,
attached to realistic but fictional schools and local education agencies. Do
these data sets unduly perpetuate any demographic biases or demographic skew
with respect to key student performance indicators?

To this end, we have developed a [Jupyter Notebook](https://jupyter.org/) for
performing rigorous statistical analysis on an ODS database:

* [Ed-Fi Sample Data Equity Analysis](Equity-Analysis.ipynb)

Detailed write-ups will be provided here on all three Ed-Fi sample data sets,
once available.

## Getting Started

* Requires Python 3.9 or 3.10
* Requires [Poetry](https://python-poetry.org/)
* Clone this repository, install dependencies, and launch Jupyter Notebooks

  ```bash
  git clone https://github.com/Ed-Fi-Exchange-OSS/Sample-Data-Equity-Analysis
  cd Sample-Data-Equity-Analysis
  poetry install
  poetry run jupyter notebook
  ```

  * ❗ The notebook uses IPyWidgets and does not work well in VS Code.
* A browser window will open with the Jupyter interface. Select the notebook
  there and follow the instructions in the notebook.

## Legal Information

Copyright (c) 2022 Ed-Fi Alliance, LLC and contributors.

Licensed under the [Apache License, Version 2.0](LICENSE) (the "License").

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
