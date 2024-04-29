"""Aggregate condition class and method testing"""
import time
from test.helper import utxo_mocker
from test.helper.mocked_data import (
    MOCKED_AGG_STATE_UTXO_JSON,
    MOCKED_NODE_UTXO_JSON,
    MOCKED_ORACLE_ADDRESS,
    MOCKED_ORACLE_UTXO_JSON,
)

import pytest
from charli3_offchain_core.aggregate_conditions import (
    aggregation_conditions,
    check_agg_change,
    check_agg_time,
    check_aggregation_update_time,
    check_aggregator_permission,
    check_feed_last_update,
    check_node_consensus_condition,
    check_node_updates_condition,
    check_oracle_settings,
)
from charli3_offchain_core.datums import AggDatum, NodeDatum, OracleDatum


async def get_mocked_json(mocked_json):
    """converts a blockfrost mocked response to a pycardano format"""

    utxos = utxo_mocker(MOCKED_ORACLE_ADDRESS, mocked_json)
    return utxos


@pytest.mark.asyncio
class TestAggregateConditions:
    """Testing Aggregate Conditions"""

    async def _get_oracle_settings(self):
        """internal functions to simplify parametrization"""

        utxo = await get_mocked_json(MOCKED_AGG_STATE_UTXO_JSON)

        cbor = utxo[0].output.datum.cbor.hex()

        agg_datum = AggDatum.from_cbor(cbor)

        return agg_datum.aggstate.ag_settings

    async def test_check_oracle_settings(self):
        """tests oracle settings"""

        oracle_settings = await self._get_oracle_settings()
        assert check_oracle_settings(oracle_settings)

    async def test_check_aggregation_conditions(self):
        """Testing check_feed_last_update, check_agg_time"""

        oracle_settings = await self._get_oracle_settings()

        curr_time_ms = round(time.time_ns() * 1e-6)

        oracle_utxo = await get_mocked_json(MOCKED_ORACLE_UTXO_JSON)

        oracle_datum = OracleDatum.from_cbor(oracle_utxo[0].output.datum.cbor)

        node_utxo = await get_mocked_json(MOCKED_NODE_UTXO_JSON)

        node_datum = NodeDatum.from_cbor(node_utxo[0].output.datum.cbor)

        assert check_agg_time(oracle_settings, oracle_datum, curr_time_ms)

        assert not check_feed_last_update(
            oracle_settings.os_updated_node_time, oracle_datum, curr_time_ms, node_datum
        )

        assert check_agg_change(oracle_settings, oracle_datum, 11111)

        assert check_aggregation_update_time(
            oracle_settings, oracle_datum, curr_time_ms, 11111
        )

        nodes_utxo = await get_mocked_json(MOCKED_NODE_UTXO_JSON)

        for node_utxo in nodes_utxo:
            # Casting datum is needed to go from RawCbor to NodeDatum
            node_utxo.output.datum = NodeDatum.from_cbor(
                node_utxo.output.datum.cbor.hex()
            )

        assert not check_node_updates_condition(
            oracle_settings, oracle_datum, curr_time_ms, nodes_utxo
        )

        assert check_node_consensus_condition(oracle_settings, nodes_utxo) == (
            nodes_utxo,
            411600,
        )

        # CHECKS FIRST A FAKE ADDRESS AND AFTER A CORRECT ADDRESS
        assert not check_aggregator_permission(oracle_settings, "0x0")

        assert check_aggregator_permission(
            oracle_settings,
            nodes_utxo[0].output.datum.node_state.ns_operator,
        )

        # WRAPPING ALL TESTS TOGETHER

        assert aggregation_conditions(
            oracle_settings,
            oracle_datum,
            nodes_utxo[0].output.datum.node_state.ns_operator,
            curr_time_ms,
            nodes_utxo,
        ) == ([], 0)
