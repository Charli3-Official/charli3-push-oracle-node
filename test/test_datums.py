"""Datum testing module"""

from backend.core.datums import (
    OracleDatum,
    NodeDatum,
    NodeState,
    PriceFeed,
    DataFeed,
)


class TestDatums:
    """Tests for the datum classes"""

    nodeDatum = "d87a9fd8799f581cc336a4d3ef39913b63e61f92008d5191556ed3c3c5c11b50764bc1e4d8799fd8799f1a0006476c1b00000188989d88deffffffff"  # pylint: disable=line-too-long
    oracleDatum = (
        "d8799fd87b9fa3001a0006110c011b00000185ffcd4c1b021b0000018600043a9bffff"
    )

    def test_oracle_datum(self):
        """Test the oracle datum with valid information"""
        oracle_data = OracleDatum.from_cbor(self.oracleDatum)
        assert oracle_data.price_data.get_expiry() == 1675037522587
        assert oracle_data.price_data.get_timestamp() == 1675033922587
        assert oracle_data.price_data.get_price() == 397580

    def test_node_datum(self):
        """Test the oracle datum with valid information"""
        node_operator = bytes.fromhex(
            str("c336a4d3ef39913b63e61f92008d5191556ed3c3c5c11b50764bc1e4")
        )
        node_data = NodeDatum.from_cbor(self.nodeDatum)
        assert node_data.node_state.ns_operator == node_operator
        assert node_data.node_state.ns_feed.df.df_value == 411500
        assert node_data.node_state.ns_feed.df.df_last_update == 1686187641054

    def test_node_state_attribute(self):
        """Test if the node_state attribute is correctly set in the NodeDatum class"""
        node_state = NodeState(
            ns_operator=b"operator1",
            ns_feed=PriceFeed(df=DataFeed(df_value=100, df_last_update=20210101)),
        )
        node_datum = NodeDatum(node_state=node_state)
        assert node_datum.node_state == node_state
