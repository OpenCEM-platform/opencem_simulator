Project Website: https://opencem-platform.github.io/

# OpenCEM Simulator

**OpenCEM Simulator** is the simulation component of the *Open In-Context Energy Management Platform* (OpenCEM). It provides a Python-based 
environment to emulate microgrid operation — including renewable generation, storage, and load — and to evaluate algorithm 
performance with real-world time series and context.

This repository contains the simulator implementation plus example workflows in Jupyter notebooks.

## Features

- Python API for energy system simulation  
- Example workflows showing setup and execution  
- Designed to integrate with control and decision-making strategies  
- Ideal for research and prototyping in energy management contexts

## Repository Structure
```
opencem_simulator/
├── notebooks/              # Jupyter notebooks with usage examples and tutorials
├── src/
│   └── opencem/             # OpenCEM simulator source code (Python package)
├── requirements.txt         # Python dependencies
├── .gitignore
└── README.md
```
## Getting Started

### Prerequisites

Make sure you have Python installed (>=3.8 recommended). Install dependencies with:

```bash
pip install -r requirements.txt
## Example Usage

Open the example notebooks in the notebooks/ directory using Jupyter:

```sh
jupyter notebook

```

### Dataset Usage via Simulator Classes

You can then follow the notebooks step-by-step to:

* Initialize the simulator
* Load scenario data
* Run simulations with different models

The notebooks contain instructions on how to configure the simulator and interpret results.

To validate your own control strategies you can implement a controller inheriting the Inverter Interface.

### Raw Dataset Access

The raw dataset can be found in [notebooks/opencem_dataset.7z](https://github.com/OpenCEM-platform/opencem_simulator/blob/main/notebooks/opencem_dataset.7z) which contains a Sqlite database.

Sqlite bindings are available for all major programming languages, e.g. for Python via the [sqlite3](https://docs.python.org/3/library/sqlite3.html) standard library module.

The schema of the dataset can be obtained by running the following commands using the `sqlite3` command-line utility:

```sh
sqlite3 opencem_dataset.db
```
```sql
sqlite> .tables
analog_measurements  context
sqlite> .schema analog_measurements
CREATE TABLE IF NOT EXISTS "analog_measurements" (
        "read_ts"       INTEGER,
        "inverter"      INT,
        "battvolt"      REAL,
--...
        "grid_reserve"  TEXT
);
sqlite> .schema context
CREATE TABLE IF NOT EXISTS "context" (
        "id"    INTEGER NOT NULL,
        "recorded"      INTEGER,
        "start" INTEGER,
        "end"   INTEGER,
        "value" TEXT,
        PRIMARY KEY("id" AUTOINCREMENT)
);
```

## Citation

If you use OpenCEM Simulator in research or publications, please cite the OpenCEM platform:

```bibtex
@inproceedings{10.1145/3679240.3734678,
author = {Lu, Yikai and Bartels, Tinko Sebastian and Wu, Ruixiang and Xia, Fanzeng and Wang, Xudong and Wu, Yifei and Yang, Haoxiang and Li, Tongxin},
title = {Open In-Context Energy Management Platform},
year = {2025},
isbn = {9798400711251},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
url = {https://doi.org/10.1145/3679240.3734678},
doi = {10.1145/3679240.3734678},
booktitle = {Proceedings of the 16th ACM International Conference on Future and Sustainable Energy Systems},
pages = {985–986},
numpages = {2},
keywords = {Renewable Energy Management, In-Context Learning, Control Algorithms, Photovoltaic Systems},
series = {E-Energy '25}
```
