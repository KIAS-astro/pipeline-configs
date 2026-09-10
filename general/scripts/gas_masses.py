"""
Makes a histogram of the gas particle masses. Uses the swiftsimio library.
"""

import matplotlib.pyplot as plt
import numpy as np

from swiftsimio import load

from unyt import unyt_quantity
from matplotlib.colors import LogNorm
from matplotlib.animation import FuncAnimation

def get_data(filename):
    """
    Grabs the data (masses in 10**6 Msun).
    """

    data = load(filename)

    mass_gas = data.gas.masses.to("1e9 * Msun")
    mass_split = unyt_quantity(
        float(
            data.metadata.parameters.get("SPH:particle_splitting_mass_threshold", 0.0)
        ),
        units=data.units.mass,
    ).to("1e9 * Msun")

    return mass_gas, mass_split


def make_single_image(filenames, names, number_of_simulations, output_path):
    """
    Makes a single histogram of the gas particle masses.
    """

    fig, ax = plt.subplots()
    ax.set_xlabel("Gas Particle Masses $M_{\\rm gas}$ [10$^9$ M$_\\odot$]")
    ax.set_ylabel("PDF [-]")

    data = [get_data(filename) for filename in filenames]

    # The gas particle mass depends on the simulation resolution and is not
    # known a priori, so derive the histogram range from the data rather than
    # hard-coding it. Log-spaced bins spanning the masses present show both the
    # main (near-mono-mass) peak and any lighter particle-splitting products.
    all_masses = np.concatenate([m_gas.value for m_gas, _ in data])
    all_masses = all_masses[all_masses > 0]
    m_lo, m_hi = all_masses.min(), all_masses.max()
    if m_lo == m_hi:
        m_lo, m_hi = 0.5 * m_lo, 2.0 * m_hi
    else:
        m_lo, m_hi = 0.8 * m_lo, 1.2 * m_hi
    bin_edges = np.logspace(np.log10(m_lo), np.log10(m_hi), 250)
    bins = 0.5 * (bin_edges[1:] + bin_edges[:-1])

    for (m_gas, m_split), name in zip(data, names):
        h, _ = np.histogram(m_gas, bins=bin_edges, density=True)
        (line,) = ax.plot(bins, h, label=name)
        if m_split > 0:
            ax.axvline(x=m_split, color=line.get_color(), ls="--", lw=0.2)

    ax.loglog()
    ax.legend()

    fig.savefig(f"{output_path}/gas_masses.png")

    return


if __name__ == "__main__":
    from swiftpipeline.argumentparser import ScriptArgumentParser

    arguments = ScriptArgumentParser(description="Basic gas particle mass histogram.")

    snapshot_filenames = [
        f"{directory}/{snapshot}"
        for directory, snapshot in zip(
            arguments.directory_list, arguments.snapshot_list
        )
    ]

    plt.style.use(arguments.stylesheet_location)

    make_single_image(
        filenames=snapshot_filenames,
        names=arguments.name_list,
        number_of_simulations=arguments.number_of_inputs,
        output_path=arguments.output_directory,
    )
