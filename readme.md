# MesaCAT - Mesa Agent-based Model of Flood Evacuation using OpenStreetMap

## Documentation
https://nclwater.github.io/mesacat

https://mesa.readthedocs.io/en/master/

## Dependencies
See environment.yml

`conda env create -f environment.yml -n mesacat`
`conda install --channel conda-forge --override-channels --yes fiona pyogrio`

## Run
`cd mesacat`
`python tests/test_model.py`
`python tests/test_utils.py`

## Tests
`python -m unittests discover`
