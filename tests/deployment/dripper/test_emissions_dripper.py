from datetime import datetime

import brownie
import pytest
from brownie import accounts, chain
from brownie_tokens import MintableForkToken

from helpers.addresses import registry


@pytest.fixture(scope="module")
def deployer():
    return accounts[0]


@pytest.fixture(scope="module")
def dripper():
    from scripts.deployment.deploy_emissions_dripper import main

    return main()


@pytest.fixture(scope="module")
def badger():
    return MintableForkToken(registry.eth.treasury_tokens.BADGER)


@pytest.fixture(scope="module", autouse=True)
def topup_and_fast_forward(dripper, badger):
    accounts[1].transfer(dripper, 1e18)
    badger._mint_for_testing(dripper, 100_000 * 10 ** badger.decimals())
    assert badger.balanceOf(dripper) > 0
    now = datetime.now().timestamp()
    delta = dripper.start() - now
    if delta > 0:
        # dripping period still has to start, sleep until then
        chain.sleep(delta + 60 * 60 * 24)


def test_beneficiary(dripper):
    assert dripper.beneficiary() == registry.eth.sett_vaults.remBADGER


def test_timestamps(dripper):
    assert dripper.start() > dripper.duration()


def test_duration(dripper):
    assert dripper.duration() > 0
    assert (
        dripper.start() + dripper.duration() > datetime.now().timestamp()
    ), "dripping period already expired; increase start or duration"


def test_keeper(dripper, deployer):
    assert dripper.keeper() == deployer


def test_release_from_keeper(badger, dripper, deployer):
    bal_before = badger.balanceOf(dripper.beneficiary())
    dripper.release(badger, {"from": deployer})
    assert badger.balanceOf(dripper.beneficiary()) > bal_before


def test_accounting_released(dripper, badger):
    assert dripper.released(badger, {"from": accounts[1]}) > 0


def test_release_from_techops(badger, dripper, techops):
    # just released from keeper, create a pause to build up a release again
    chain.sleep(60 * 60)
    bal_before = badger.balanceOf(dripper.beneficiary())
    dripper.release(badger, {"from": techops.account})
    assert badger.balanceOf(dripper.beneficiary()) > bal_before


def test_release_from_dev(badger, dripper, dev):
    # just released from techops, create a pause to build up a release again
    chain.sleep(60 * 60)
    bal_before = badger.balanceOf(dripper.beneficiary())
    dripper.release(badger, {"from": dev.account})
    assert badger.balanceOf(dripper.beneficiary()) > bal_before


def test_release_from_random(badger, dripper):
    with brownie.reverts():
        bal_before = badger.balanceOf(dripper.beneficiary())
        dripper.release(badger, {"from": accounts[1]})
        assert badger.balanceOf(dripper.beneficiary()) > bal_before


def test_set_keeper_from_dev(dripper, dev):
    dripper.setKeeper(accounts[1], {"from": dev.account})


def test_set_keeper_from_techops(dripper, techops):
    dripper.setKeeper(accounts[1], {"from": techops.account})


def test_set_keeper_from_random(dripper):
    with brownie.reverts():
        dripper.setKeeper(accounts[1], {"from": accounts[1]})


def test_sweep_eth_from_dev(dripper, dev):
    bal_before = dev.account.balance()
    dripper.sweep({"from": dev.account})
    assert dev.account.balance() > bal_before
    assert dripper.balance() == 0


def test_sweep_eth_from_random(dripper):
    with brownie.reverts():
        dripper.sweep({"from": accounts[1]})


def test_sweep_erc_from_dev(dripper, badger, dev):
    bal_before = badger.balanceOf(dev)
    dripper.sweep(badger, {"from": dev.account})
    assert badger.balanceOf(dev) > bal_before
    assert badger.balanceOf(dripper) == 0


def test_sweep_erc_from_random(dripper, badger):
    with brownie.reverts():
        dripper.sweep(badger, {"from": accounts[1]})
