from pybinding.constants import hbar

a = 0.24595   #: [nm] unit cell length
a_cc = 0.142  #: [nm] carbon-carbon distance
t = -2.8    #: [eV] nearest neighbour hopping
vf = 3 / (2 * hbar) * abs(t) * a_cc  #: [nm/s] Fermi velocity
