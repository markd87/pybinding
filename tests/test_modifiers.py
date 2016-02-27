import pytest

import numpy as np
import pybinding as pb
from pybinding.repository import graphene


one, zero = np.ones(1), np.zeros(1)
complex_one = np.ones(1, dtype=np.complex64)


def build_model(*params):
    model = pb.Model(graphene.monolayer(), *params)
    model.report()
    return model


def assert_position(x, y, z):
    assert np.allclose(x, [0, 0])
    assert np.allclose(y, [-graphene.a_cc / 2, graphene.a_cc / 2])
    assert np.allclose(z, [0, 0])


def assert_sublattice(sub_id, model):
    assert np.allclose(sub_id, [0, 1])

    assert np.argwhere(sub_id == model.lattice['A']) == 0
    assert np.argwhere(sub_id != model.lattice['A']) == 1
    assert np.argwhere(sub_id == 'A') == 0
    assert np.argwhere(sub_id != 'A') == 1

    with pytest.raises(KeyError):
        assert sub_id == 'invalid_sublattice_name'


def assert_hoppings(hop_id, model):
    assert np.all(hop_id == 0)

    assert np.all(hop_id == model.lattice('t'))
    assert not np.any(hop_id != model.lattice('t'))
    assert np.all(hop_id == 't')
    assert not np.any(hop_id != 't')

    with pytest.raises(KeyError):
        assert hop_id == 'invalid_hopping_name'


def test_decorator():
    pb.onsite_energy_modifier(lambda energy: energy)
    with pytest.raises(RuntimeError) as excinfo:
        pb.onsite_energy_modifier(lambda this_is_unexpected: None)
    assert "Unexpected argument" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        pb.onsite_energy_modifier(lambda energy, x, y, z, w: None)
    assert "Unexpected argument" in str(excinfo.value)

    pb.onsite_energy_modifier(lambda energy: energy + 1)
    with pytest.raises(RuntimeError) as excinfo:
        pb.onsite_energy_modifier(lambda: 1)
    assert "Modifier must return numpy.ndarray" in str(excinfo.value)

    pb.site_position_modifier(lambda x, y, z: (x, y, z))
    with pytest.raises(RuntimeError) as excinfo:
        pb.site_position_modifier(lambda x, y, z: (x, y))
    assert "expected to return 3 ndarray(s), but got 2" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        pb.onsite_energy_modifier(lambda: (one, one))
    assert "expected to return 1 ndarray(s), but got 2" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        pb.onsite_energy_modifier(lambda x: np.zeros(x.size / 2))
    assert "must return the same shape" in str(excinfo.value)

    pb.hopping_energy_modifier(lambda energy: np.ones_like(energy, dtype=np.complex128))
    with pytest.raises(RuntimeError) as excinfo:
        pb.onsite_energy_modifier(lambda energy: np.ones_like(energy, dtype=np.complex128))
    assert "must not return complex" in str(excinfo.value)


@pb.site_state_modifier
def global_mod(state):
    return np.ones_like(state)


def test_callsig():
    assert "global_mod()" == str(global_mod)
    assert "global_mod()" == repr(global_mod)

    @pb.site_state_modifier
    def local_mod(state):
        return np.ones_like(state)
    assert "test_callsig()" == str(local_mod)
    assert "test_callsig()" == repr(local_mod)

    def wrapped_mod(a, b):
        @pb.site_state_modifier
        def actual_mod(state):
            return np.ones_like(state) * a * b
        return actual_mod
    assert "wrapped_mod(a=1, b=8)" == str(wrapped_mod(1, 8))
    assert "test_callsig.<locals>.wrapped_mod(a=1, b=8)" == repr(wrapped_mod(1, 8))


def test_cast():
    @pb.hopping_energy_modifier
    def complex_in_real_out(energy):
        return np.ones_like(energy, dtype=np.float64)

    assert np.isrealobj(complex_in_real_out(complex_one))
    assert np.iscomplexobj(complex_in_real_out.apply(complex_one, zero, zero, zero))
    assert not complex_in_real_out.is_complex()

    @pb.hopping_energy_modifier
    def real_in_complex_out(energy):
        return np.ones_like(energy, dtype=np.complex128)

    assert np.iscomplexobj(real_in_complex_out(complex_one))
    assert np.iscomplexobj(real_in_complex_out.apply(complex_one, zero, zero, zero))
    assert real_in_complex_out.is_complex()


def test_site_state():
    @pb.site_state_modifier
    def mod(state):
        return np.ones_like(state)
    assert np.all(mod(zero))
    assert np.all(mod.apply(zero, one, one, one, one))

    capture = []

    @pb.site_state_modifier
    def check_args(state, x, y, z, sub_id, sites):
        capture[:] = (v.copy() for v in (state, x, y, z, sub_id))
        capture.append(sites.argsort_nearest([0, graphene.a_cc / 2]))
        return state

    model = build_model(check_args)
    assert model.hamiltonian.dtype == np.float32

    state, x, y, z, sub_id, nearest = capture
    assert np.all(state == [True, True])
    assert_position(x, y, z)
    assert_sublattice(sub_id, model)
    assert np.all(nearest == [1, 0])


def test_site_position():
    @pb.site_position_modifier
    def mod(x, y, z):
        return x + 1, y + 1, z + 1
    assert (one,) * 3 == mod(zero, zero, zero)
    assert (one,) * 3 == mod.apply(zero, zero, zero, one)

    capture = []

    @pb.site_position_modifier
    def check_args(x, y, z, sub_id, sites):
        capture[:] = (v.copy() for v in (x, y, z, sub_id))
        capture.append(sites.argsort_nearest([0, graphene.a_cc / 2]))
        return x, y, z

    model = build_model(check_args)
    assert model.hamiltonian.dtype == np.float32

    x, y, z, sub_id, nearest = capture
    assert_position(x, y, z)
    assert_sublattice(sub_id, model)
    assert np.all(nearest == [1, 0])


def test_onsite():
    @pb.onsite_energy_modifier
    def mod(energy):
        return energy + 2
    assert np.all(2 == mod(zero))
    assert np.all(2 == mod.apply(zero, zero, zero, zero, one))

    capture = []

    @pb.onsite_energy_modifier
    def check_args(energy, x, y, z, sub_id, sites):
        capture[:] = (v.copy() for v in (energy, x, y, z, sub_id))
        capture.append(sites.argsort_nearest([0, graphene.a_cc / 2]))
        return energy

    model = build_model(check_args)
    assert model.hamiltonian.dtype == np.float32

    energy, x, y, z, sub_id, nearest = capture
    assert np.allclose(energy, [0, 0])
    assert_position(x, y, z)
    assert_sublattice(sub_id, model)
    assert np.all(nearest == [1, 0])

    @pb.onsite_energy_modifier(double=True)
    def make_double(energy):
        return energy

    model = build_model(make_double)
    assert model.hamiltonian.dtype == np.float64


def test_hopping_energy():
    @pb.hopping_energy_modifier
    def mod(energy):
        return energy * 2
    assert np.all(2 == mod(one))
    assert np.all(2 == mod.apply(one, zero, zero, zero, zero, zero, zero, zero))

    capture = []

    @pb.hopping_energy_modifier
    def check_args(energy, hop_id, x1, y1, z1, x2, y2, z2):
        capture[:] = (v.copy() for v in (energy, hop_id, x1, y1, z1, x2, y2, z2))
        return energy

    model = build_model(check_args)
    assert model.hamiltonian.dtype == np.float32

    energy, hop_id, x1, y1, z1, x2, y2, z2 = capture
    assert np.allclose(energy, graphene.t)
    assert_hoppings(hop_id, model)
    assert np.allclose(x1, 0)
    assert np.allclose(y1, -graphene.a_cc / 2)
    assert np.allclose(z1, 0)
    assert np.allclose(x2, 0)
    assert np.allclose(y2, graphene.a_cc / 2)
    assert np.allclose(z2, 0)

    @pb.hopping_energy_modifier(double=True)
    def make_double(energy):
        return energy

    model = build_model(make_double)
    assert model.hamiltonian.dtype == np.float64

    @pb.hopping_energy_modifier
    def make_complex(energy):
        return energy * 1j

    model = build_model(make_complex)
    assert model.hamiltonian.dtype == np.complex64

    @pb.hopping_energy_modifier(double=True)
    def make_complex_double(energy):
        return energy * 1j

    model = build_model(make_complex_double)
    assert model.hamiltonian.dtype == np.complex128


# Disabled for now. It doesn't work when the 'fast math' compiler flag is set.
def dont_test_invalid_return():
    @pb.onsite_energy_modifier
    def mod_inf(energy):
        return np.ones_like(energy) * np.inf

    with pytest.raises(RuntimeError) as excinfo:
        build_model(mod_inf)
    assert "NaN or INF" in str(excinfo.value)

    @pb.onsite_energy_modifier
    def mod_nan(energy):
        return np.ones_like(energy) * np.NaN

    with pytest.raises(RuntimeError) as excinfo:
        build_model(mod_nan)
    assert "NaN or INF" in str(excinfo.value)
