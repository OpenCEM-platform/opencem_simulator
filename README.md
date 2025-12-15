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

You can then follow the notebooks step-by-step to:

* Initialize the simulator
* Load scenario data
* Run simulations with different models

The notebooks contain instructions on how to configure the simulator and interpret results.

To validate your own control strategies you can overwrite inherit the Inverter Interface.

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
