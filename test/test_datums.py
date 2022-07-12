"""Datum testing module"""

from backend.api.datums import OracleDatum, NodeDatum

class TestDatums():
    """Tests for the datum classes"""
    nodeDatum = ("d87a9fd8799fd8799f581c1e5d17616b1a98b8314412"
                 "c980ae1feaa95b1e441ffc350b756ef8c5ffd8799f"
                 "d8799f1a000a12201b000001816356a63fffffffff")
    oracleDatum = ("d87b9fd8799fd8799fd8799f1a000927c01b00000181635"
                   "732dfffffd8799f1b0000018163622f5fff80d87a80ffff")

    def test_oracle_datum(self):
        """Test the oracle datum with valid information"""
        oracle_data=OracleDatum.from_cbor(self.oracleDatum)
        assert oracle_data.expiry_date == 1655229787999
        assert oracle_data.oracle_feed.timestamp == 1655229067999
        assert oracle_data.oracle_feed.value == 600000

    def test_node_datum(self):
        """Test the oracle datum with valid information"""
        node_operator = '1e5d17616b1a98b8314412c980ae1feaa95b1e441ffc350b756ef8c5'
        node_data=NodeDatum.from_cbor(self.nodeDatum)
        assert node_data.node_operator == node_operator
        assert node_data.node_feed.value == 660000
        assert node_data.node_feed.timestamp == 1655229031999
