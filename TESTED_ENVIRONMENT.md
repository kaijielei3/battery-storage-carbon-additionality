# Tested software environment

The verification and figure-regeneration scripts in this release were tested with:

- Python 3.13.5
- NumPy 2.3.5
- pandas 2.2.3
- SciPy 1.17.0
- Matplotlib 3.10.8

Install the listed Python packages with:

```bash
python -m pip install -r 04_Executable_Code/requirements.txt
```

The original optimization run's complete software environment was not recorded in the
supplied archive. The versions above describe the environment used to test this prepared
repository; they should not be read as a claim about the exact environment used for the
original 212 archived solves.

HiGHS is called through `scipy.optimize.linprog`. Different SciPy/HiGHS builds or tolerances
may return a different cost-equivalent optimum. Compare the model constraints, objective,
emissions totals, and feasibility tolerances rather than expecting every dispatch variable
to be bit-for-bit identical.
