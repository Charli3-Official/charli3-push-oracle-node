import pytest
from backend.api.datums import *

class TestDatums():
    nodeDatum = 'd87a9fd8799fd8799f581c1e5d17616b1a98b8314412c980ae1feaa95b1e441ffc350b756ef8c5ffd8799fd8799f1a000a12201b000001816356a63fffffffff'
    oracleDatum = 'd87b9fd8799fd8799fd8799f1a000927c01b00000181635732dfffffd8799f1b0000018163622f5fff80d87a80ffff'

    def test_oracleDatum(self):
        oracleData=OracleDatum(self.oracleDatum)
        assert oracleData.expiryDate == 1655229787999
        assert oracleData.oracleFeed.timestamp == 1655229067999
        assert oracleData.oracleFeed.value == 600000
    
    def test_nodeDatum(self):
        nodeData=NodeDatum(self.nodeDatum)
        assert nodeData.nodeOperator == '1e5d17616b1a98b8314412c980ae1feaa95b1e441ffc350b756ef8c5'
        assert nodeData.nodeFeed.value == 660000
        assert nodeData.nodeFeed.timestamp == 1655229031999