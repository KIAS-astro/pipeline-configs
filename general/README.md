General pipeline config
=======================

This is a **model-agnostic** pipeline config for any SWIFT hydrodynamics
simulation. It was distilled from the `flamingo/` config by keeping only the
scripts that rely on quantities present in essentially *any* SWIFT hydro+BH
run — in particular a standard **EAGLE-model** run performed with SWIFT.

Unlike `flamingo/` and `colibre/`, this config does **not** reference any
subgrid-model-specific snapshot fields (BH spins/jets, kinetic SN feedback
kick velocities, subgrid temperatures, HI/H2 masses, ...), so it should run
out of the box on a plain EAGLE run.

What is included
----------------

Snapshot-based (use `swiftsimio` to read the `.hdf5` snapshot):

- **Density-Temperature**: `density_temperature`, `density_temperature_metals`,
  `density_internal_energy`, `density_pressure`
- **Metal mass fractions**: `metallicity_distribution`
- **Stellar feedback** (needs the EAGLE variable-`f_E` feedback model, i.e. the
  `EAGLEFeedback:*` / `EAGLEStarFormation:*` parameters): `birth_density_f_E`,
  `birth_density_distribution`, `birth_density_metallicity`
- **Black holes**: `bh_masses` (dynamical vs subgrid mass)
- **Histograms**: `gas_masses`, `gas_smoothing_lengths`

Log-file based (read the on-the-fly text logs SWIFT writes):

- From `SFR.txt` / `statistics.txt`: `star_formation_history`,
  `stellar_mass_evolution`, `gas_metallicity_evolution`,
  `star_metallicity_evolution`, `bh_metallicity_evolution`,
  `bh_accretion_evolution`, `bh_mass_evolution`
- From `timesteps.txt` (pure run performance, fully model-agnostic):
  `particle_updates_step_cost`, `wallclock_simulation_time`,
  `wallclock_number_of_steps`, `simulation_time_number_of_steps`,
  `wallclock_timebin_hist`, `deadtime_timebin_hist`, `stepsize_deadtime`,
  `deadtime_evolution`

`load_sfh_data.py` is a helper module imported by `star_formation_history.py`.

What is deliberately NOT included (and why)
-------------------------------------------

These stay in `flamingo/` (or `colibre/`) because they need fields a standard
EAGLE run does not write:

- **Detailed BH physics** — `bh_spins*`, `bh_jet_*`, `bh_accretion_modes`,
  `bh_eddington_fractions`, `bh_luminosities`, `bh_radio_luminosity_functions`,
  `bh_thermal_*`, `bh_misalignment_angles`, `bh_merger_mass_fractions`.
  These need the FLAMINGO BH model (spins, jets, accretion modes, efficiencies).
- **Kinetic SN feedback** — `last_SNII_kick_velocity_distribution`,
  `max_SNII_kick_velocities`. These need `(Last|Maximal)SNIIKineticFeedbackvKick`
  (COLIBRE / newer models, not standard EAGLE thermal feedback).
- **Subgrid ISM / chemistry** — `subgrid_density_temperature`,
  `HI_mass_evolution`, `H2_mass_evolution`. These need subgrid T/rho and HI/H2
  mass columns (COLIBRE).
- **Optional tracers** — `max_temperatures`, `feedback_SNII_events`,
  `feedback_AGN_events`. These need `MaximalTemperatures` / `HeatedBy*Feedback`,
  which are only written if the run was compiled/configured to record them. If
  your run does record them, you can copy these three across too.

How to run it on your EAGLE run
-------------------------------

First, build the observational data once (from the repo root):

```bash
git submodule update --init --recursive
cd observational_data && ./convert.py && cd ..
```

`SFR.txt`, `statistics.txt` and `timesteps.txt` are expected in the input
directory for the log-based figures.

### No halo catalogue? Use `run_pipeline.py` (recommended here)

`swift-pipeline` **requires** a VELOCIraptor/SOAP catalogue (`-c`) and loads it
unconditionally, even when no scaling-relation figures are produced. If you only
have snapshots and logs, use the bundled catalogue-free runner instead. It reads
`config.yml` and calls each script directly (all figures in this config are
catalogue-free), then writes an `index.html`:

```bash
python general/run_pipeline.py \
  -i /path/to/your/run \
  -s snapshot_XXXX.hdf5 \
  -n "My EAGLE run" \
  -o /path/to/output \
  -j 8
```

Options: `--only density_temperature.py ...` to run a subset, `--debug` to print
each script's output. When you later produce a catalogue, either add the
catalogue-based figures to `config.yml` or switch to `swift-pipeline` below.

### With a halo catalogue: full `swift-pipeline`

```bash
swift-pipeline \
  -C general \
  -i /path/to/your/run \
  -s snapshot_XXXX.hdf5 \
  -c halo_XXXX.properties \
  -n "My EAGLE run" \
  -o /path/to/output \
  -j 8
```

Notes
-----

- The auto-plotter (VELOCIraptor/SOAP scaling relations) is intentionally empty
  here — those figures need a halo catalogue and are model/catalogue specific.
- If a particular figure still errors because a field is missing in your
  snapshot, just remove that entry from `config.yml`.
