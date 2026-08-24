# ORBIS — Earth Observation Wildfire Intelligence

**Current Release:** v12.0.0-GOLDEN
**Status:** Feature-frozen research prototype

ORBIS is a wildfire ignition-risk research platform combining environmental physics, Earth observation data, machine learning, spatial analysis, and probability calibration.

The goal of ORBIS is to investigate whether environmental and geographic indicators can be combined to identify locations exhibiting elevated wildfire ignition conditions.

> **Important:** ORBIS is a research and decision-support prototype. It is not an emergency response system, evacuation authority, fire-line tracking system, or government-certified wildfire prediction service.

---

## What ORBIS Does

ORBIS combines multiple environmental inputs, including:

* Temperature
* Relative humidity
* Wind speed
* Vapor Pressure Deficit (VPD)
* Equilibrium Moisture Content (EMC)
* Sentinel-2 NDVI
* Terrain slope
* Historical fire observations

The system uses these variables to estimate wildfire ignition risk and provide an interpretable probability output.

---

## System Architecture

The ORBIS pipeline is designed around several data sources:

**NASA FIRMS**
Historical active-fire detections used to establish fire-event observations.

**ERA5 / ERA5-Land**
Historical atmospheric conditions used to reconstruct environmental conditions surrounding fire events.

**Sentinel-2**
Vegetation observations used to derive NDVI and represent vegetation/fuel conditions.

**SRTM**
Terrain elevation data used to derive slope.

**Open-Meteo**
Live weather and forecast telemetry for the operational dashboard.

The overall workflow is:

```text
Earth Observation Data
        ↓
Spatial / Temporal Feature Extraction
        ↓
Physics-Derived Variables
        ↓
XGBoost Risk Model
        ↓
Probability Calibration
        ↓
Spatial / Temporal Validation
        ↓
ORBIS Risk Probability
```

---

## Physics Layer

ORBIS does not rely exclusively on raw machine-learning inputs.

The model incorporates derived physical indicators including:

### Vapor Pressure Deficit

VPD represents the atmospheric demand for moisture and is used as an indicator of atmospheric drying conditions.

### Equilibrium Moisture Content

EMC estimates the moisture equilibrium of dead fuel under the prevailing atmospheric conditions.

These variables allow ORBIS to represent relationships between heat, atmospheric dryness, wind and fuel conditions rather than relying exclusively on raw meteorological measurements.

---

## Machine Learning

The current v12.0.0-GOLDEN architecture uses gradient-boosted decision trees with probability calibration.

Model probabilities are calibrated so that predicted probabilities can be evaluated against observed outcomes rather than being treated simply as uncalibrated classifier scores.

The released model artifacts include:

```text
orbis_calibrated_model.joblib
orbis_base_xgb_model.joblib
model_metadata.json
```

The calibrated model is used for probability inference.

The base XGBoost model is retained for model explanation and diagnostic analysis.

---

## Validation

ORBIS uses multiple validation concepts rather than relying on training accuracy.

### Spatial validation

Geographic grouping is used to reduce spatial leakage between training and evaluation data.

### Paired backtesting

Fire observations can be compared against matched non-fire control observations to test whether ORBIS assigns greater risk to the observed fire environment.

### Synthetic physics holdout

v12.0.0-GOLDEN includes a controlled synthetic physics holdout used to evaluate model behaviour under a known simulated environment.

### Current synthetic holdout results

The frozen v12.0.0-GOLDEN benchmark produced:

| Metric      |     Result |
| ----------- | ---------: |
| ROC-AUC     | **0.8048** |
| Brier Score | **0.1352** |
| Log-Loss    | **0.4230** |

These results are from an **independently generated synthetic physics holdout** and are not measurements of real-world wildfire prediction accuracy.

### Real empirical backtesting

Earlier empirical paired backtesting has produced substantially weaker performance than the synthetic benchmark.

This is expected to be treated as an important limitation rather than hidden or removed from the project.

The next validation phase is focused on genuinely unseen historical observations.

---

## v12.0.0-GOLDEN Freeze

The v12.0.0-GOLDEN release represents a deliberate model-development freeze.

The core architecture and model configuration are not intended to be repeatedly modified simply to improve benchmark scores.

Future changes should be driven by:

* New empirical evidence
* Independent validation
* Data-quality improvements
* Reproducibility findings
* External testing

rather than repeated tuning against the same evaluation data.

---

## Running ORBIS

### Requirements

Python 3.x with the dependencies listed in:

```text
requirements.txt
```

### Authenticate Earth Engine

The Earth Engine components require an authenticated Google Earth Engine / Google Cloud environment.

The current development project uses:

```text
orbis-506314
```

Do not publish private authentication credentials or service-account keys.

### Run the research / validation pipeline

The project contains separate components for:

```text
Data extraction
Model training
Backtesting / evaluation
Operational dashboard
```

The exact execution order is documented within the project scripts.

### Run the dashboard

```powershell
py -m streamlit run app.py
```

The dashboard provides interactive environmental risk assessment using live telemetry and the released model artifacts.

---

## Project Structure

A typical ORBIS repository contains:

```text
Orbis/
├── app.py
├── orbis_cli.py
├── train_model.py
├── requirements.txt
├── model_metadata.json
├── orbis_calibrated_model.joblib
├── orbis_base_xgb_model.joblib
├── Validation/
│   ├── evaluate_model.py
│   └── ...
└── ...
```

---

## Limitations

ORBIS has important limitations.

The model cannot guarantee that a wildfire will or will not occur.

Wildfire ignition and spread depend on factors that may not be fully represented in the current tabular model, including:

* Human ignition behaviour
* Lightning
* Fine-scale fuel structure
* Fuel management
* Microclimate
* Ember transport
* Local wind phenomena
* Detection uncertainty
* Spatial and temporal differences between datasets

Satellite active-fire observations also represent detected thermal events rather than a perfect record of every ignition.

---

## Research Status

ORBIS should currently be considered a **research artifact and early-stage decision-support prototype**.

The project is transitioning from model development toward:

1. Independent empirical validation
2. Reproducibility testing
3. External user testing
4. Technical review
5. Potential future institutional or commercial applications

No claim is made that ORBIS is scientifically proven to predict all wildfire ignitions.

---

## Release

**Current frozen release:**

```text
v12.0.0-GOLDEN
```

The release is intended to provide a stable baseline for independent testing and future empirical validation.

---

## Author / Project

**ORBIS**

Earth Observation Wildfire Intelligence Research Platform

This repository documents the development of the ORBIS wildfire-risk research system and its progression from prototype modelling toward independent empirical validation.
