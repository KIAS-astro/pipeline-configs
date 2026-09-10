Quickstart — `general` pipeline (no catalogue needed)
=====================================================

Make diagnostic figures from a finished SWIFT run using only its **snapshots
and log files** — no VELOCIraptor/SOAP halo catalogue required.

`swift-pipeline` insists on loading a catalogue, so this config ships its own
`run_pipeline.py`, which reads `config.yml` and calls each plotting script
directly. See `README.md` for the full list of figures and what each needs.

---

1. One-time setup
-----------------

```bash
# get the repo + this branch on the machine you'll run on
git clone git@github.com:KIAS-astro/pipeline-configs.git
cd pipeline-configs
git checkout add-general-config

# python environment
conda create -n pipeline python=3.11 -y   # or a venv
conda activate pipeline
pip install swiftpipeline pyyaml
python -c "import swiftsimio, yaml; print('env ok')"
```

The `observational_data` submodule is **optional** (adds observation points to a
few figures only). You can skip it — see README.

2. Check what you have
----------------------

The input directory needs the snapshot(s) plus the log files `SFR.txt`,
`statistics.txt`, `timesteps.txt`. Find the snapshot names / redshifts:

```bash
python - <<'EOF'
import glob, h5py
RUN = "/path/to/your/run"
for f in sorted(glob.glob(f"{RUN}/*.hdf5"))[-3:]:
    z = h5py.File(f, "r")["Header"].attrs["Redshift"]
    print(f, "z=%.4f" % float(z))
EOF
```

3. Smoke test (2 figures, verbose)
----------------------------------

Always do this first to confirm paths/fields before the full run:

```bash
python general/run_pipeline.py \
  -i /path/to/your/run \
  -s snapshot_XXXX.hdf5 \
  -n "My run" \
  -o /path/to/output \
  --only density_temperature.py star_formation_history.py --debug
```

Both `[ ok ]` → you're good. (A `\mu` SyntaxWarning is harmless.)

4. Full run — all 26 figures
----------------------------

Drop `--only`. Run on a **compute node** (phase diagrams read every gas
particle). Example SLURM script `run.sh`:

```bash
#!/bin/bash
#SBATCH --job-name=pipeline
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G            # raise if the largest box OOMs
#SBATCH --time=03:00:00
#SBATCH --output=pipeline_%j.log
# #SBATCH --partition=xxx    # set for your cluster
# #SBATCH --account=xxx

source ~/.bashrc
conda activate pipeline
cd /path/to/pipeline-configs

python general/run_pipeline.py \
  -i /path/to/your/run \
  -s snapshot_XXXX.hdf5 \
  -n "My run" \
  -o /path/to/output \
  -j ${SLURM_CPUS_PER_TASK}
```

Submit: `sbatch run.sh`. Output is 26 PNGs + `index.html` in the output dir.

5. Compare several runs in one report
-------------------------------------

Repeat `-i`/`-s`/`-n` (must be equal length, snapshots at the **same redshift**).
Scatter/phase plots become side-by-side panels; line plots overplot.

```bash
BASE=/gpfs/dbi224/swift_eagle_flamingo
python general/run_pipeline.py \
  -i $BASE/eagle_spin_jet $BASE/eagle $BASE/flamingo \
  -s snap_0274.hdf5 snap_0274.hdf5 flamingo_0274.hdf5 \
  -n "EAGLE spin-jet" "EAGLE" "FLAMINGO" \
  -o /gpfs/dbi224/pipeline_output/compare_z0 \
  -j 8
```

---

Useful flags & troubleshooting
------------------------------

| Flag | Meaning |
|------|---------|
| `-i` | Input director(y/ies) with snapshot(s) + `*.txt` logs |
| `-s` | Snapshot filename(s), no directory; match `-i` in length |
| `-n` | Legend name(s) |
| `-o` | Output directory (figures + `index.html`) |
| `-j` | Number of scripts to run in parallel |
| `--only a.py b.py` | Run only these scripts |
| `--debug` | Print each script's full stdout/stderr |

- **Only N figures came out?** You probably left `--only` on — drop it for all 26.
- **A script shows `[FAIL]`** — usually a field/column missing in that run. The
  end of the run prints the stderr tail; remove that entry from `config.yml` or
  exclude it, the rest still run.
- **OOM on the biggest box** — raise `--mem`, or first run the cheap ones:
  `--only star_formation_history.py stellar_mass_evolution.py deadtime_evolution.py ...`
- **Have a catalogue later?** Switch to full `swift-pipeline -C general ... -c halo_XXXX.properties` (see README).
