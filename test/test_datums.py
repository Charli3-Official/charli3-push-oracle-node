"""Datum testing module"""

from backend.core.datums import (
    OracleDatum,
    NodeDatum,
    NodeState,
    PriceFeed,
    DataFeed,
    NodeInfo,
)


class TestDatums:
    """Tests for the datum classes"""

    nodeDatum = "d87a9fd8799fd8799f581c37080314efda7753fa4ef1f8a19ec9b7e92376d06778e18d456b946dffd8799fd8799f1a0005e4921b00000185fba69d23ffffffff"
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
        node_info = NodeInfo(
            bytes.fromhex(
                str("37080314efda7753fa4ef1f8a19ec9b7e92376d06778e18d456b946d")
            )
        )
        node_data = NodeDatum.from_cbor(self.nodeDatum)
        assert node_data.node_state.node_operator == node_info
        assert node_data.node_state.node_feed.df.df_value == 386194
        assert node_data.node_state.node_feed.df.df_last_update == 1674964278563

    def test_node_state_attribute(self):
        """Test if the node_state attribute is correctly set in the NodeDatum class"""
        node_state = NodeState(
            node_operator=b"operator1",
            node_feed=PriceFeed(df=DataFeed(df_value=100, df_last_update=20210101)),
        )
        node_datum = NodeDatum(node_state=node_state)
        assert node_datum.node_state == node_state
